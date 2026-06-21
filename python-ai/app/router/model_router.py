"""
Model Router
============

Selects an AI provider per request based on data sensitivity, latency budget,
and cost ceiling. This is the component that makes the project genuinely
multi-cloud: the agent never names a model, it asks the router for a completion
and the router decides.

Default reasoning model: Claude Sonnet 4.6 on AWS Bedrock.
Alternates: GPT-4o-class on Azure OpenAI, Gemini on Vertex AI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from app.providers.bedrock import BedrockProvider
from app.providers.azure_openai import AzureOpenAIProvider
from app.providers.vertex import VertexProvider

logger = logging.getLogger(__name__)


class Sensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RoutingRequest:
    prompt: str
    system: str | None = None
    sensitivity: Sensitivity = Sensitivity.MEDIUM
    latency_budget_ms: int = 8000
    cost_ceiling_usd: float = 0.05
    max_tokens: int = 1500


@dataclass
class RoutingDecision:
    provider: str
    model: str
    reason: str


class ModelRouter:
    """Provider-agnostic entry point for every model call in the system."""

    # Default reasoning model. Swapping this is config, not code.
    DEFAULT = ("bedrock", "anthropic.claude-sonnet-4-6")

    def __init__(self) -> None:
        self._providers = {
            "bedrock": BedrockProvider(),
            "azure_openai": AzureOpenAIProvider(),
            "vertex": VertexProvider(),
        }

    def _decide(self, req: RoutingRequest) -> RoutingDecision:
        """
        Routing policy:
          - HIGH sensitivity  -> Bedrock/Claude (kept inside the AWS data boundary,
                                 strongest reasoning for risk-bearing assessment).
          - LOW sensitivity + tight cost ceiling -> Vertex/Gemini (cheap bulk
                                 classification where a wrong call is low blast-radius).
          - Bedrock unavailable in region -> Azure OpenAI fallback.
          - Everything else -> default (Claude Sonnet 4.6 on Bedrock).
        """
        if req.sensitivity == Sensitivity.HIGH:
            return RoutingDecision(
                "bedrock", "anthropic.claude-sonnet-4-6",
                "High-sensitivity assessment kept on Bedrock/Claude inside AWS boundary",
            )
        if req.sensitivity == Sensitivity.LOW and req.cost_ceiling_usd < 0.01:
            return RoutingDecision(
                "vertex", "gemini-2.0-flash",
                "Low-sensitivity bulk classification routed to cost-optimized Gemini",
            )
        if not self._providers["bedrock"].is_available():
            return RoutingDecision(
                "azure_openai", "gpt-4o",
                "Bedrock unavailable in region; failing over to Azure OpenAI",
            )
        return RoutingDecision(*self.DEFAULT, "Default reasoning path")

    async def complete(self, req: RoutingRequest) -> dict:
        decision = self._decide(req)
        logger.info("Routing -> %s/%s: %s", decision.provider, decision.model, decision.reason)
        provider = self._providers[decision.provider]
        result = await provider.complete(
            prompt=req.prompt,
            system=req.system,
            model=decision.model,
            max_tokens=req.max_tokens,
        )
        # Attach the routing decision and cost so the Java core can meter it.
        result["routing"] = {
            "provider": decision.provider,
            "model": decision.model,
            "reason": decision.reason,
        }
        return result
