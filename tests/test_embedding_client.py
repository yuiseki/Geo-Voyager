import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from geo_voyager.embedding_client import EmbeddingClient


def response(payload):
    result = MagicMock()
    result.read.return_value = json.dumps(payload).encode('utf-8')
    return result


@pytest.mark.parametrize('base_url', ['http://embedding:8080', 'http://embedding:8080/', 'http://embedding:8080/v1', 'http://embedding:8080/v1/'])
def test_single_embedding_and_configured_request(base_url):
    with patch('geo_voyager.embedding_client.urlopen') as http:
        http.return_value.__enter__.return_value = response({'data': [{'index': 0, 'embedding': [1, 0.5]}]})
        vectors = EmbeddingClient(base_url=base_url, model='embedding-model').embed(['日本語の文章'])
    assert vectors == [[1.0, 0.5]]
    assert all(type(value) is float for value in vectors[0])
    http.assert_called_once()
    request = http.call_args.args[0]
    assert request.full_url == 'http://embedding:8080/v1/embeddings'
    assert request.get_method() == 'POST'
    assert request.get_header('Content-type') == 'application/json'
    assert json.loads(request.data) == {'model': 'embedding-model', 'input': ['日本語の文章'], 'encoding_format': 'float'}


def test_batch_returns_vectors_in_input_index_order():
    with patch('geo_voyager.embedding_client.urlopen') as http:
        http.return_value.__enter__.return_value = response({'data': [
            {'index': 1, 'embedding': [0.3, 0.4]}, {'index': 0, 'embedding': [0.1, 0.2]},
        ]})
        assert EmbeddingClient('http://embedding', 'model').embed(['文1', '文2']) == [[0.1, 0.2], [0.3, 0.4]]
    assert json.loads(http.call_args.args[0].data)['input'] == ['文1', '文2']
    http.assert_called_once()


def test_empty_input_fails_without_http():
    with patch('geo_voyager.embedding_client.urlopen') as http:
        with pytest.raises(ValueError):
            EmbeddingClient('http://embedding', 'model').embed([])
    http.assert_not_called()


def test_http_error_is_propagated():
    with patch('geo_voyager.embedding_client.urlopen', side_effect=HTTPError('url', 500, 'failure', {}, None)):
        with pytest.raises(HTTPError):
            EmbeddingClient('http://embedding', 'model').embed(['文章'])


def test_invalid_json_is_rejected():
    with patch('geo_voyager.embedding_client.urlopen') as http:
        http.return_value.__enter__.return_value.read.return_value = b'{broken'
        with pytest.raises(json.JSONDecodeError):
            EmbeddingClient('http://embedding', 'model').embed(['文章'])


@pytest.mark.parametrize('payload', [
    None, {}, {'data': None}, {'data': []},
    {'data': [{'index': 0, 'embedding': [1]}]},
    {'data': [{'index': 0, 'embedding': []}, {'index': 1, 'embedding': [1]}]},
    {'data': [{'index': 0, 'embedding': [1, 2]}, {'index': 1, 'embedding': [1]}]},
    {'data': [{'index': 0, 'embedding': [1]}, {'index': 0, 'embedding': [2]}]},
    {'data': [{'index': -1, 'embedding': [1]}, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': 0, 'embedding': [1]}, {'index': 2, 'embedding': [2]}]},
    {'data': [{'embedding': [1]}, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': False, 'embedding': [1]}, {'index': 1, 'embedding': [2]}]},
    {'data': [None, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': 0, 'embedding': 'vector'}, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': 0, 'embedding': ['1']}, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': 0, 'embedding': [True]}, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': 0, 'embedding': [float('nan')]}, {'index': 1, 'embedding': [2]}]},
    {'data': [{'index': 0, 'embedding': [float('inf')]}, {'index': 1, 'embedding': [2]}]},
])
def test_invalid_response_is_rejected(payload):
    with patch('geo_voyager.embedding_client.urlopen') as http:
        http.return_value.__enter__.return_value = response(payload)
        with pytest.raises(ValueError):
            EmbeddingClient('http://embedding', 'model').embed(['文1', '文2'])
