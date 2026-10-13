import json
from urllib.request import Request, urlopen

# Code generation has a long tail with Qwen3.8-27B: median 19 s, p99 107 s, and some calls over 120 s, which ended
# the whole Goal. Measured from the exploration logs of 2026-10-11.
TIMEOUT_SECONDS = 300
# Temperature 0 repeats only when the server does not reuse a cached prompt prefix: after another prompt with the same
# prefix, the same prompt got a different reply (measured on gvt-llm, 2026-10-14). The cost is the prefix's prefill.
CACHE_PROMPT = False


class LlamaTruncated(ValueError):
    """The reply stopped at max_tokens (finish_reason length), so it is cut off, not finished."""


class LlamaClient:
    def generate(self, prompt: str, *, temperature: float | None = None,
                 enable_thinking: bool | None = None, system_prompt: str | None = None,
                 max_tokens: int | None = None, reasoning_budget_tokens: int | None = None,
                 assistant_prefix: str | None = None, refuse_truncated: bool = False) -> str:
        """refuse_truncated: raise LlamaTruncated instead of returning a reply cut at max_tokens. Code cut off this
        way can still parse and run, so code generation asks for it."""
        payload = {"model": "gvt-llm", "messages": [{"role": "user", "content": prompt}]}
        if system_prompt is not None:
            payload['messages'].insert(0, {'role': 'system', 'content': system_prompt})
        if assistant_prefix is not None:
            payload['messages'].append({'role': 'assistant', 'content': assistant_prefix})
        payload['cache_prompt'] = CACHE_PROMPT
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
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
        choice = data["choices"][0]
        if refuse_truncated and choice.get("finish_reason") == "length":
            raise LlamaTruncated(f'the reply reached max_tokens ({max_tokens}) and was cut off')
        return choice["message"]["content"]
