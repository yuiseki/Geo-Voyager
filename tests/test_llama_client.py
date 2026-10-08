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
