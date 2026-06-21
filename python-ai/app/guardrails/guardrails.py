"""
Guardrails
==========

Runs before any prompt reaches a model and after any completion returns.

  - Inbound:  PII redaction + prompt-injection screening.
  - Outbound: output validation (must be parseable assessment JSON; no leaked
              instructions; no fabricated cited-policy IDs outside the corpus).

In a regulated deployment these would be backed by a dedicated DLP service and a
managed guardrail (e.g. Bedrock Guardrails). Here they are explicit so a reviewer
can see the control points.
"""

from __future__ import annotations

import re

# Conservative PII patterns for the demo. Real deployments use a DLP engine.
_PII_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),          # Indian PAN
    "CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

# Crude prompt-injection heuristics. Layered defence, not the only defence.
_INJECTION_SIGNS = [
    "ignore previous instructions",
    "disregard the system prompt",
    "you are now",
    "reveal your system prompt",
    "act as",
]


class GuardrailViolation(Exception):
    pass


def redact_pii(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    redacted = text
    for label, pattern in _PII_PATTERNS.items():
        if pattern.search(redacted):
            found.append(label)
            redacted = pattern.sub(f"[REDACTED:{label}]", redacted)
    return redacted, found


def screen_injection(text: str) -> None:
    lowered = text.lower()
    for sign in _INJECTION_SIGNS:
        if sign in lowered:
            raise GuardrailViolation(f"Possible prompt injection detected: '{sign}'")


def validate_output(text: str, allowed_policy_ids: set[str]) -> None:
    """Outbound: any cited policy ID must exist in the retrieved corpus."""
    cited = set(re.findall(r"BIAN-[A-Z0-9-]+", text))
    invented = cited - allowed_policy_ids
    if invented:
        raise GuardrailViolation(f"Model cited policy IDs not in corpus: {invented}")


def apply_inbound(text: str) -> str:
    screen_injection(text)
    redacted, _ = redact_pii(text)
    return redacted
