from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from geo_voyager.dataset import Dataset
from geo_voyager.dataset_graph import DatasetGraph
from geo_voyager.fetch_gateway import HubRedirect, make_handler


@pytest.fixture
def gateway():
    graph = DatasetGraph()
    graph.register(Dataset(
        id="test/fixed", description="固定データ", url="http://origin:8000/fixed.txt",
        license="CC0", formats=("text",), spatial_coverage="なし",
        temporal_coverage="なし", contents=("テスト文字列",),
    ))
    response = MagicMock()
    response.status = 200
    response.headers = {"Content-Type": "text/plain", "Content-Length": "10"}
    response.read.return_value = b"0123456789"
    with patch("geo_voyager.fetch_gateway.build_opener") as build:
        upstream = build.return_value.open
        upstream.return_value.__enter__.return_value = response
        with patch.object(graph, "get", wraps=graph.get) as get:
            server = HTTPServer(("127.0.0.1", 0), make_handler(graph))
            thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
            thread.start()
            try:
                yield server.server_port, upstream, response, get
            finally:
                server.shutdown()
                thread.join()
                server.server_close()


def request(gateway, method="GET", path="/datasets/test/fixed", headers=None):
    connection = HTTPConnection("127.0.0.1", gateway[0], timeout=2)
    try:
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_get_uses_only_registered_url(gateway):
    assert request(gateway)[::2] == (200, b"0123456789")
    gateway[3].assert_called_once_with("test/fixed")
    gateway[1].assert_called_once()
    upstream_request = gateway[1].call_args.args[0]
    assert upstream_request.full_url == "http://origin:8000/fixed.txt"
    assert upstream_request.get_method() == "GET"


def test_head_returns_no_body(gateway):
    status, headers, body = request(gateway, "HEAD", headers={"Range": "bytes=0-4"})
    assert status == 200 and body == b""
    assert headers["Content-Length"] == "10"
    gateway[2].read.assert_not_called()
    upstream_request = gateway[1].call_args.args[0]
    assert upstream_request.get_method() == "HEAD"
    assert upstream_request.headers == {}


def test_get_forwards_only_range(gateway):
    gateway[2].status = 206
    gateway[2].headers = {"Content-Range": "bytes 0-4/10", "Content-Length": "5"}
    gateway[2].read.return_value = b"01234"
    status, headers, body = request(gateway, headers={
        "Range": "bytes=0-4", "Authorization": "secret", "X-Target-URL": "http://other/",
    })
    assert status == 206 and body == b"01234"
    assert headers["Content-Range"] == "bytes 0-4/10"
    assert gateway[1].call_args.args[0].headers == {"Range": "bytes=0-4"}


def test_unknown_dataset_is_rejected(gateway):
    assert request(gateway, path="/datasets/unknown/dataset")[0] == 404
    gateway[1].assert_not_called()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutating_methods_are_rejected(gateway, method):
    assert request(gateway, method)[0] == 405
    gateway[1].assert_not_called()


@pytest.mark.parametrize("path", [
    "/datasets/test/fixed?url=http://other/",
    "/datasets/test/fixed?anything=1",
    "/datasets/http%3A%2F%2Fother%2F",
    "/?url=http://other/",
])
def test_worker_cannot_specify_an_arbitrary_url(gateway, path):
    assert request(gateway, path=path)[0] in (400, 404)
    gateway[1].assert_not_called()


def test_redirect_to_another_host_is_not_followed_or_forwarded(gateway):
    handler = HubRedirect()
    request_ = MagicMock(full_url="https://huggingface.co/datasets/x/resolve/abc/a.parquet")
    for target in ("http://other/", "https://evil.example/a", "https://hf.co.evil.example/a",
                   "http://us.aws.cdn.hf.co/a"):
        assert handler.redirect_request(request_, None, 302, "Found", {}, target) is None
    gateway[1].side_effect = HTTPError("http://origin:8000/fixed.txt", 302, "Found", {"Location": "http://other/"}, None)
    status, headers, _ = request(gateway)
    assert status == 502
    assert "Location" not in headers
    gateway[1].assert_called_once()


def test_redirect_to_the_hub_cdn_is_followed_with_range():
    from urllib.request import Request

    handler = HubRedirect()
    original = Request("https://huggingface.co/datasets/x/resolve/abc/a.parquet", headers={"Range": "bytes=0-4"})
    for target in ("https://us.aws.cdn.hf.co/xet-bridge-us/abc?Signature=1",
                   "https://cdn-lfs.huggingface.co/repos/abc"):
        followed = handler.redirect_request(original, None, 302, "Found", {}, target)
        assert followed.full_url == target
        assert followed.get_header("Range") == "bytes=0-4"


def test_redirect_from_a_non_hub_origin_is_not_followed():
    handler = HubRedirect()
    request_ = MagicMock(full_url="https://origin.example/a")
    assert handler.redirect_request(request_, None, 302, "Found", {}, "https://us.aws.cdn.hf.co/a") is None


def test_gateway_prefers_registered_data_url_over_card_url(gateway):
    from dataclasses import replace

    # 元の get を wrap した mock に、指定した登録レコードを返させる。
    graph_dataset = Dataset(
        id="test/fixed", description="固定データ", url="http://origin:8000/card",
        license="CC0", formats=("text",), spatial_coverage="なし",
        temporal_coverage="なし", contents=("テスト文字列",),
    )
    gateway[3].return_value = replace(graph_dataset, data_url="http://origin:8000/fixed.txt")
    assert request(gateway)[0] == 200
    assert gateway[1].call_args.args[0].full_url == "http://origin:8000/fixed.txt"
