"""
Assessment Agent
================

The multi-step agent loop. This is what makes the system *agentic* rather than a
single LLM call: it plans, classifies, retrieves grounding, assesses, and
produces a recommendation — and it surfaces a gating signal so the Java control
plane can decide whether a human must approve before the result is committed.

Steps:
  1. classify   — what is this component, what stack
  2. retrieve   — pull grounding patterns from the corpus (RAG)
  3. assess     — anti-patterns + risk score, grounded in retrieved patterns
  4. recommend  — target-state mapping + migration sequence with cited IDs
  5. gate       — emit needs_human_approval if risk/blast-radius exceeds threshold

Every model call goes through the router, so no provider is hard-coded here.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from app.router.model_router import ModelRouter, RoutingRequest, Sensitivity
from app.rag.retriever import PatternRetriever
from app.guardrails import guardrails

logger = logging.getLogger(__name__)

RISK_GATE_THRESHOLD = 6  # risk_score >= this routes to a human approver

_SYSTEM = (
    "You are an enterprise architecture assessment assistant for a regulated "
    "financial institution. You classify legacy components, identify "
    "anti-patterns, and propose target-state mappings. You only cite pattern IDs "
    "that appear in the provided grounding context. You never auto-approve a "
    "migration; you produce a recommendation for human review. Respond with "
    "strict JSON only."
)


@dataclass
class AssessmentResult:
    component: str
    steps: list[dict] = field(default_factory=list)
    recommendation: dict | None = None
    total_cost_usd: float = 0.0
    needs_human_approval: bool = False

    def record(self, step: str, output: dict) -> None:
        self.steps.append({"step": step, "routing": output.get("routing"),
                           "cost_usd": output.get("cost_usd", 0.0)})
        self.total_cost_usd = round(self.total_cost_usd + output.get("cost_usd", 0.0), 6)


class AssessmentAgent:
    def __init__(self) -> None:
        self._router = ModelRouter()
        self._retriever = PatternRetriever()

    async def run(self, component_description: str) -> AssessmentResult:
        clean = guardrails.apply_inbound(component_description)
        result = AssessmentResult(component=clean[:80])

        # 1 + 2: classify (low sensitivity, cheap path eligible) then retrieve
        classify_prompt = (
            f"Classify this legacy component and name its stack. Component:\n{clean}\n"
            "Return JSON: {\"classification\": ..., \"stack\": ...}"
        )
        classify_out = await self._router.complete(RoutingRequest(
            prompt=classify_prompt, system=_SYSTEM,
            sensitivity=Sensitivity.LOW, cost_ceiling_usd=0.005, max_tokens=300))
        result.record("classify", classify_out)
        classification = _safe_json(classify_out["text"])

        grounding = self._retriever.retrieve(
            query=f"{clean} {classification.get('classification','')}", k=3)
        grounding_text = "\n".join(f"[{g['id']}] {g['title']}: {g['body']}" for g in grounding)

        # 3 + 4: assess + recommend (high sensitivity -> Bedrock/Claude)
        assess_prompt = (
            f"Component:\n{clean}\n\nClassification: {json.dumps(classification)}\n\n"
            f"Grounding patterns (cite only these IDs):\n{grounding_text}\n\n"
            "Identify anti-patterns, assign an integer risk_score 1-10 reflecting "
            "migration blast radius, map to a target-state service domain, and give "
            "a migration sequence. Return JSON with keys: anti_patterns (list), "
            "risk_score (int), target_state (string), cited_patterns (list of IDs), "
            "migration_sequence (list), rationale (string)."
        )
        assess_out = await self._router.complete(RoutingRequest(
            prompt=assess_prompt, system=_SYSTEM,
            sensitivity=Sensitivity.HIGH, max_tokens=1200))
        result.record("assess_and_recommend", assess_out)

        guardrails.validate_output(assess_out["text"], self._retriever.allowed_ids())
        recommendation = _safe_json(assess_out["text"])
        recommendation["classification"] = classification
        recommendation["grounding"] = [g["id"] for g in grounding]
        result.recommendation = recommendation

        # 5: gate
        risk = int(recommendation.get("risk_score", 0) or 0)
        result.needs_human_approval = risk >= RISK_GATE_THRESHOLD
        logger.info("Assessment risk=%s gate=%s", risk, result.needs_human_approval)
        return result


def _safe_json(text: str) -> dict:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text, "_parse_error": True}
