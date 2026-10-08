from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from geo_voyager.datasets import load_dataset_graph
from integration.admin_download import register_admin_download


@pytest.mark.parametrize("location", [
    "https://us.aws.cdn.hf.co/xet-bridge-us/repository/contenthash?Expires=123",
])
def test_admin_download_registers_only_the_verified_hugging_face_cdn_url(location):
    graph = load_dataset_graph()
    source = graph.get("yuiseki/jp-admin-2026-09").data_url
    with patch("integration.admin_download.build_opener") as build:
        build.return_value.open.side_effect = HTTPError(
            source, 302, "Found", {"Location": location, "X-Xet-Hash": "contenthash"}, None,
        )
        register_admin_download(graph)
    assert graph.get("yuiseki/jp-admin-2026-09").data_url == location
    request = build.return_value.open.call_args.args[0]
    assert request.full_url == source and request.get_method() == "HEAD"
    build.return_value.open.assert_called_once()


@pytest.mark.parametrize("location", [
    "https://other.example/xet-bridge-us/repository/contenthash",
    "http://us.aws.cdn.hf.co/xet-bridge-us/repository/contenthash",
    "https://us.aws.cdn.hf.co/xet-bridge-us/repository/another-file",
    "https://user@us.aws.cdn.hf.co/xet-bridge-us/repository/contenthash",
])
def test_admin_download_rejects_unrelated_redirect_targets(location):
    graph = load_dataset_graph()
    source = graph.get("yuiseki/jp-admin-2026-09").data_url
    with patch("integration.admin_download.build_opener") as build:
        build.return_value.open.side_effect = HTTPError(
            source, 302, "Found", {"Location": location, "X-Xet-Hash": "contenthash"}, None,
        )
        with pytest.raises(ValueError):
            register_admin_download(graph)
    assert graph.get("yuiseki/jp-admin-2026-09").data_url == source
