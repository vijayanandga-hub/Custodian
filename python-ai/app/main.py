"""
FastAPI AI plane entrypoint.

Exposes the assessment agent to the Java control plane over internal REST.
The Java core calls /assess, applies governance, and gates on needs_human_approval.
"""
from __future__ import annotations

import logging
from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.assessment_agent import AssessmentAgent
from app.guardrails.guardrails import GuardrailViolation

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Custodian — AI Plane", version="0.1.0")
_agent = AssessmentAgent()


class AssessRequest(BaseModel):
    component_description: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/assess")
async def assess(req: AssessRequest) -> dict:
    try:
        result = await _agent.run(req.component_description)
    except GuardrailViolation as exc:
        return {"error": "guardrail_violation", "detail": str(exc)}
    return {
        "component": result.component,
        "recommendation": result.recommendation,
        "steps": result.steps,
        "total_cost_usd": result.total_cost_usd,
        "needs_human_approval": result.needs_human_approval,
    }
