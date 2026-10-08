from unittest.mock import MagicMock, patch

import pytest

from geo_voyager.control_primitives import call_service
from geo_voyager.services import HTTP_USER_AGENT


def test_primitive_calls_only_gateway_and_returns_text():
    response = MagicMock()
    response.read.return_value = b'{"data":[]}'
    with patch('geo_voyager.control_primitives.call_service.urlopen') as open_request:
        open_request.return_value.__enter__.return_value = response
        assert call_service('taginfo', path='/api/4/tags/list', params={'query': 'volcano'}) == '{"data":[]}'
        req = open_request.call_args.args[0]
        assert req.full_url == 'http://gateway:8000/services/taginfo/api/4/tags/list?query=volcano'
        assert req.get_header('User-agent') == HTTP_USER_AGENT
        assert req.get_method() == 'GET'


def test_primitive_posts_body_and_content_type():
    with patch('geo_voyager.control_primitives.call_service.urlopen') as opened:
        opened.return_value.__enter__.return_value.read.return_value = b'ok'
        assert call_service('overpass', path='api/interpreter', body='data=query',
                            content_type='application/x-www-form-urlencoded') == 'ok'
        req = opened.call_args.args[0]
        assert req.get_method() == 'POST' and req.data == b'data=query'
        assert req.get_header('Content-type') == 'application/x-www-form-urlencoded'


@pytest.mark.parametrize('service,path', [('unknown', 'api/status'), ('https://evil', ''),
    ('overpass', 'https://evil'), ('overpass', '//evil/api/interpreter'),
    ('overpass', '../admin'), ('overpass', '%2f%2fevil'), ('overpass', '/api/interpreter?url=evil')])
def test_arbitrary_urls_and_unknown_services_are_rejected_before_http(service, path):
    with patch('geo_voyager.control_primitives.call_service.urlopen') as opened:
        with pytest.raises((ValueError, KeyError)):
            call_service(service, path=path)
        opened.assert_not_called()


def test_primitive_returns_bounded_http_error_details_to_execution_failure():
    from io import BytesIO
    from urllib.error import HTTPError
    with patch('geo_voyager.control_primitives.call_service.urlopen') as opened:
        opened.side_effect = HTTPError('http://gateway', 400, 'bad query', {}, BytesIO(b'Unknown output format count'))
        with pytest.raises(RuntimeError, match='Unknown output format count'):
            call_service('overpass', path='/api/interpreter')
