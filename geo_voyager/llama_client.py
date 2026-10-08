import json
from urllib.request import Request, urlopen


class LlamaClient:
    def generate(self, prompt: str, *, temperature: float | None = None,
                 enable_thinking: bool | None = None, system_prompt: str | None = None,
                 max_tokens: int | None = None, reasoning_budget_tokens: int | None = None,
                 assistant_prefix: str | None = None) -> str:
        payload = {"model": "gvt-llm", "messages": [{"role": "user", "content": prompt}]}
        if system_prompt is not None:
            payload['messages'].insert(0, {'role': 'system', 'content': system_prompt})
        if assistant_prefix is not None:
            payload['messages'].append({'role': 'assistant', 'content': assistant_prefix})
        if temperature is not None:
            payload['temperature'] = temperature
        if enable_thinking is not None:
            payload['chat_template_kwargs'] = {'enable_thinking': enable_thinking}
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        if reasoning_budget_tokens is not None:
            payload['reasoning_budget_tokens'] = reasoning_budget_tokens
        request = Request(
            "http://10.108.45.102:8080/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            data = json.load(response)
        return data["choices"][0]["message"]["content"]
