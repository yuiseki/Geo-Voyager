import json
from unittest.mock import MagicMock, patch

from geo_voyager.llama_client import LlamaClient


def test_client_posts_free_text_prompt_and_returns_content():
    response = MagicMock()
    response.read.return_value = json.dumps(
        {"choices": [{"message": {"content": " 仮説本文\n"}}]}
    ).encode()
    with patch("geo_voyager.llama_client.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value = response

        result = LlamaClient().generate("疑問から仮説を提案してください")

    assert result == " 仮説本文\n"
    urlopen.assert_called_once()
    request = urlopen.call_args.args[0]
    assert request.full_url == "http://10.108.45.102:8080/v1/chat/completions"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {
        "model": "gvt-llm",
        "messages": [
            {"role": "user", "content": "疑問から仮説を提案してください"}
        ],
    }


def test_client_can_explicitly_request_deterministic_sampling():
    response = MagicMock()
    response.read.return_value = b'{"choices":[{"message":{"content":"code"}}]}'
    with patch('geo_voyager.llama_client.urlopen') as opened:
        opened.return_value.__enter__.return_value = response
        assert LlamaClient().generate('code please', temperature=0.0) == 'code'
        assert json.loads(opened.call_args.args[0].data)['temperature'] == 0.0


def test_client_can_disable_thinking_per_request_without_structured_output():
    response = MagicMock()
    response.read.return_value = b'{"choices":[{"message":{"content":"code"}}]}'
    with patch('geo_voyager.llama_client.urlopen') as opened:
        opened.return_value.__enter__.return_value = response
        assert LlamaClient().generate('code please', enable_thinking=False) == 'code'
        payload = json.loads(opened.call_args.args[0].data)
        assert payload['chat_template_kwargs'] == {'enable_thinking': False}
        assert 'response_format' not in payload and 'grammar' not in payload


def test_client_can_separate_generation_instruction_from_user_metadata():
    response = MagicMock()
    response.read.return_value = b'{"choices":[{"message":{"content":"code"}}]}'
    with patch('geo_voyager.llama_client.urlopen') as opened:
        opened.return_value.__enter__.return_value = response
        assert LlamaClient().generate('metadata', system_prompt='Write executable code') == 'code'
        assert json.loads(opened.call_args.args[0].data)['messages'] == [
            {'role': 'system', 'content': 'Write executable code'},
            {'role': 'user', 'content': 'metadata'},
        ]


def test_client_bounds_generation_and_reasoning_without_schema():
    response = MagicMock()
    response.read.return_value = b'{"choices":[{"message":{"content":"code"}}]}'
    with patch('geo_voyager.llama_client.urlopen') as opened:
        opened.return_value.__enter__.return_value = response
        assert LlamaClient().generate('code please', max_tokens=3072, reasoning_budget_tokens=1024) == 'code'
        payload = json.loads(opened.call_args.args[0].data)
        assert payload['max_tokens'] == 3072
        assert payload['reasoning_budget_tokens'] == 1024
        assert 'grammar' not in payload and 'response_format' not in payload


def test_client_can_prefill_a_free_text_assistant_prefix():
    response = MagicMock()
    response.read.return_value = b'{"choices":[{"message":{"content":"complete response"}}]}'
    with patch('geo_voyager.llama_client.urlopen') as opened:
        opened.return_value.__enter__.return_value = response
        assert LlamaClient().generate('write code', assistant_prefix='description:\n') == 'complete response'
        payload = json.loads(opened.call_args.args[0].data)
        assert payload['messages'][-1] == {'role': 'assistant', 'content': 'description:\n'}
        assert 'response_format' not in payload and 'grammar' not in payload
