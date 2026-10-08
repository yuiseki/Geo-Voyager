import json
from urllib.request import Request, urlopen


class LlamaClient:
    def generate(self, prompt: str) -> str:
        request = Request(
            "http://10.108.45.102:8080/v1/chat/completions",
            data=json.dumps(
                {
                    "model": "gvt-llm",
                    "messages": [{"role": "user", "content": prompt}],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            data = json.load(response)
        return data["choices"][0]["message"]["content"]
