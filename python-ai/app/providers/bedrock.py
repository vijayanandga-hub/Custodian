"""
AWS Bedrock provider — Claude Sonnet 4.6.

Uses the Bedrock Messages API. If credentials are absent the provider returns a
deterministic stub so the full agent + governance flow can be demonstrated with
zero cloud spend (useful for reviewers cloning the repo).
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# Approx Bedrock pricing for Claude Sonnet 4.6 (USD per 1K tokens). Used only for
# cost metering/estimation in the demo; keep in config in a real deployment.
PRICE_IN_PER_1K = 0.003
PRICE_OUT_PER_1K = 0.015


class BedrockProvider:
    def __init__(self) -> None:
        self._region = os.getenv("AWS_REGION", "us-east-1")
        self._client = None
        try:
            import boto3  # imported lazily so stub mode needs no AWS deps
            if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"):
                self._client = boto3.client("bedrock-runtime", region_name=self._region)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bedrock client not initialised, using stub mode: %s", exc)

    def is_available(self) -> bool:
        return self._client is not None

    async def complete(self, prompt: str, system: str | None, model: str, max_tokens: int) -> dict:
        if self._client is None:
            return self._stub(prompt, model)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        response = self._client.invoke_model(
            modelId=model,
            body=json.dumps(body),
        )
        payload = json.loads(response["body"].read())
        text = payload["content"][0]["text"]
        usage = payload.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        return {
            "text": text,
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
            "cost_usd": round(in_tok / 1000 * PRICE_IN_PER_1K + out_tok / 1000 * PRICE_OUT_PER_1K, 6),
            "provider": "bedrock",
            "model": model,
        }

    def _stub(self, prompt: str, model: str) -> dict:
        logger.info("Bedrock STUB returning canned assessment output")
        text = (
            '{"classification": "integration-service", "stack": "Java/Spring legacy", '
            '"anti_patterns": ["shared-database", "synchronous-coupling"], '
            '"target_state": "BIAN Payment Order service domain, event-driven", '
            '"risk_score": 7, "rationale": "Shared DB and synchronous fan-out create '
            'a high blast-radius coupling that must be broken before migration."}'
        )
        return {
            "text": text,
            "usage": {"input_tokens": 420, "output_tokens": 110},
            "cost_usd": 0.00291,
            "provider": "bedrock-stub",
            "model": model,
        }
