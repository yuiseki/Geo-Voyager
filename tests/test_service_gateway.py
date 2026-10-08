from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from geo_voyager.service_gateway import make_handler, MAX_RESPONSE_BYTES, MAX_REQUEST_BYTES
from geo_voyager.services import load_service_graph, HTTP_USER_AGENT


@pytest.fixture
def gateway():
    graph = load_service_graph()
    response = MagicMock(status=200, headers={'Content-Type': 'application/json'})
    response.read.return_value = b'{"ok":true}'
    with patch('geo_voyager.service_gateway.build_opener') as opener:
        upstream = opener.return_value.open
        upstream.return_value.__enter__.return_value = response
        server = HTTPServer(('127.0.0.1', 0), make_handler(graph))
        thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        try:
            yield server.server_port, upstream, response
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


def request(gateway, path='/services/taginfo/api/4/site/info', method='GET', body=None, headers=None):
    with closing(HTTPConnection('127.0.0.1', gateway[0], timeout=3)) as connection:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()


def test_get_registered_service_preserves_query_and_custom_user_agent(gateway):
    assert request(gateway, '/services/taginfo/api/4/tags/list?query=volcano')[0] == 200
    req = gateway[1].call_args.args[0]
    assert req.full_url == 'https://taginfo.yuiseki.net/api/4/tags/list?query=volcano'
    assert req.get_header('User-agent') == HTTP_USER_AGENT
    assert gateway[1].call_args.kwargs['timeout'] == 15
    gateway[2].read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_post_forwards_query_body_only_to_read_query_endpoint(gateway):
    body = 'data=[out:json];node(0,0,1,1);out;'
    assert request(gateway, '/services/overpass/api/interpreter', 'POST', body,
                   {'Content-Type': 'application/x-www-form-urlencoded', 'X-Target-URL': 'http://other'})[0] == 200
    req = gateway[1].call_args.args[0]
    assert req.full_url == 'https://overpass.yuiseki.net/api/interpreter'
    assert req.data.decode() == body and req.get_method() == 'POST'
    assert 'X-target-url' not in req.headers


@pytest.mark.parametrize('path', [
    '/services/unknown/api/4/site/info', '/services/other.yuiseki.net/api/status',
    '/services/http%3A%2F%2Fevil/api/status', '/services/taginfo//evil/path',
    '/services/taginfo/http://evil/', '/services/taginfo/api/4/../admin',
    '/services/taginfo/api/4/%2e%2e/admin', '/services/taginfo/api/4/site/info?url=http://evil',
    '/services/taginfo/api/4/site/info?endpoint=http://evil',
    'http://evil/services/taginfo/api/4/site/info',
])
def test_unknown_and_arbitrary_targets_are_rejected(gateway, path):
    assert request(gateway, path)[0] in (400, 404, 405)
    gateway[1].assert_not_called()


@pytest.mark.parametrize('method', ['PUT', 'PATCH', 'DELETE', 'CONNECT', 'OPTIONS'])
def test_mutation_methods_rejected(gateway, method):
    assert request(gateway, method=method)[0] == 405
    gateway[1].assert_not_called()


@pytest.mark.parametrize('path', ['/services/overpass/api/kill_my_queries', '/services/yuisekin-geosparql/geo/update',
    '/services/yuisekin-geosparql/$/datasets', '/services/nominatim/import', '/services/valhalla/admin'])
def test_mutating_paths_are_rejected_even_with_post(gateway, path):
    assert request(gateway, path, 'POST', 'x')[0] in (400, 405)
    gateway[1].assert_not_called()


def test_taginfo_post_not_enabled(gateway):
    assert request(gateway, method='POST', body='x')[0] == 405
    gateway[1].assert_not_called()


def test_sparql_update_media_type_rejected(gateway):
    assert request(gateway, '/services/yuisekin-geosparql/geo/sparql', 'POST', 'DELETE WHERE {?s ?p ?o}',
                   {'Content-Type': 'application/sparql-update'})[0] == 415
    gateway[1].assert_not_called()


def test_redirects_not_followed_or_returned(gateway):
    gateway[1].side_effect = HTTPError('https://taginfo.yuiseki.net', 302, 'redirect', {'Location': 'http://evil'}, None)
    status, headers, _ = request(gateway)
    assert status == 502 and 'Location' not in headers
    gateway[1].assert_called_once()


def test_response_limit(gateway):
    gateway[2].read.return_value = b'x' * (MAX_RESPONSE_BYTES + 1)
    assert request(gateway)[0] == 502


def test_request_limit(gateway):
    assert request(gateway, '/services/overpass/api/interpreter', 'POST', b'x' * (MAX_REQUEST_BYTES + 1))[0] == 413
    gateway[1].assert_not_called()


def test_timeout_is_explicit_failure(gateway):
    gateway[1].side_effect = TimeoutError()
    assert request(gateway)[0] == 504
