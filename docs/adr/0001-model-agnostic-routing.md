# ADR 0001 — Model-agnostic routing

## Status
Accepted

## Context
The agent needs an LLM for classification, assessment, and recommendation. The
institution operates across AWS, Azure, and GCP, has data-residency constraints
that differ by workload sensitivity, and is under cost pressure. Hard-coding a
single model would couple the agent to one provider's availability, pricing, and
regional footprint — unacceptable for a control that must keep running.

## Decision
The agent never names a model. It calls a **router** that selects a provider per
request based on data sensitivity, latency budget, and cost ceiling:

- High-sensitivity assessment stays on **Claude Sonnet 4.6 (Bedrock)** inside the
  AWS boundary, where reasoning quality matters most.
- Low-sensitivity bulk classification can route to **Gemini (Vertex)** when the
  cost ceiling is tight and a wrong call has low blast radius.
- **GPT-4o (Azure OpenAI)** is the fail-over when Bedrock is unavailable in region.

## Consequences
- Provider independence is demonstrated, not asserted. Swapping the default is a
  config change, not a code change.
- Cost is actively governed: cheap work goes to cheap models, risk-bearing work
  goes to the strongest model.
- Added complexity: a routing policy that must be tested and observable. The
  routing decision is logged and audited on every call.
