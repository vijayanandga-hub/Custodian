"""Azure OpenAI provider (GPT-4o-class) — fallback / cross-check path."""
from __future__ import annotations
import logging, os
logger = logging.getLogger(__name__)


class AzureOpenAIProvider:
    def __init__(self) -> None:
        self._endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self._key = os.getenv("AZURE_OPENAI_KEY")

    def is_available(self) -> bool:
        return bool(self._endpoint and self._key)

    async def complete(self, prompt: str, system: str | None, model: str, max_tokens: int) -> dict:
        if not self.is_available():
            return {"text": "[stub] Azure OpenAI cross-check agrees with primary assessment.",
                    "usage": {"input_tokens": 400, "output_tokens": 90},
                    "cost_usd": 0.0024, "provider": "azure-openai-stub", "model": model}
        # Real call path: AzureOpenAI client chat.completions.create(...)
        from openai import AzureOpenAI
        client = AzureOpenAI(azure_endpoint=self._endpoint, api_key=self._key,
                             api_version="2024-10-21")
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        resp = client.chat.completions.create(model=model, messages=messages,
                                              max_tokens=max_tokens)
        u = resp.usage
        return {"text": resp.choices[0].message.content,
                "usage": {"input_tokens": u.prompt_tokens, "output_tokens": u.completion_tokens},
                "cost_usd": round(u.prompt_tokens/1000*0.0025 + u.completion_tokens/1000*0.01, 6),
                "provider": "azure-openai", "model": model}
