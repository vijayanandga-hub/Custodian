# Custodian — Agentic Architecture Assessment Gateway for BFSI

*Governed agentic assessment for legacy modernization — provenance, guardrails, and human approval around every AI decision.*

> A model-agnostic, governance-first agent that ingests a legacy application's
> architecture, classifies its components, maps them to a target-state pattern
> (BIAN / cloud-native microservices), flags anti-patterns, and produces a
> **migration recommendation that a human must approve before it is committed.**

This is a reference implementation, not a toy. It demonstrates how an agentic AI
workflow gets deployed inside a regulated financial institution: every model call
is routed by sensitivity/cost/latency, every step is audited, every high-impact
recommendation is gated behind human approval, and every request carries an
attached token-cost record.

---

## Why this exists

Modernization assessments — "what does this legacy system contain, what should it
become, and what's risky about getting there" — are slow, expensive, and
inconsistent. They are also a *good* fit for an agent: the work is multi-step and
decision-heavy rather than a single prompt. But in BFSI you cannot let a model
auto-commit an architecture decision. So the interesting engineering is not the
LLM call — it's the **governance layer around it**.

That layer is the point of this repository.

---

## Architecture at a glance

```
                    ┌──────────────────────────────────────────────┐
                    │            Java Core (Spring Boot)           │
   request ─────────▶  Gateway → Policy Enforcement → Approval SM  │
                    │      │            │                 │        │
                    │   Audit Log   Cost Meter      Human-in-loop   │
                    └──────┼─────────────────────────────┼─────────┘
                           │ (REST, internal)            │
                    ┌──────▼─────────────────────────────▼─────────┐
                    │           Python AI Service (FastAPI)        │
                    │   Model Router → Guardrails → RAG → Agent     │
                    │        │                                      │
                    │   ┌────┴─────┬───────────┬──────────┐         │
                    │ Bedrock   Azure OpenAI  Vertex AI    (routed) │
                    │ (Claude)   (GPT-4o)     (Gemini)              │
                    └──────────────────────────────────────────────┘
```

**Deliberate split of responsibility:**

- **Java (Spring Boot) core** owns enterprise integration, policy enforcement,
  the human-approval state machine, audit persistence, and cost metering. This is
  where governance lives.
- **Python (FastAPI) AI service** owns model routing, guardrails, retrieval, and
  the agent loop. This is where the AI ecosystem lives.

This is how a real enterprise actually draws the line: the system-of-record and
control plane in the JVM, the AI plane in Python.

---

## The agentic workflow

A modernization assessment runs as a multi-step agent, not a single call:

1. **Intake** — ingest a component inventory / architecture description.
2. **Classify** — label each component (presentation, API, integration, data,
   batch, legacy-monolith fragment) and detect technology stack.
3. **Retrieve** — RAG over a target-state pattern corpus (BIAN service domains,
   cloud-native patterns, anti-pattern catalogue).
4. **Assess** — flag anti-patterns (shared DB, chatty integration, god-service,
   synchronous coupling) and score migration risk per component.
5. **Recommend** — produce a target-state mapping + migration sequence with
   cited evidence from the retrieved corpus.
6. **Gate** — anything above a configurable risk/blast-radius threshold is routed
   to a **human approver** before the recommendation is marked committed.

Every step emits an audit event and a token-cost record.

---

## Models used (and why)

| Plane | Provider | Model | Used for |
|-------|----------|-------|----------|
| Default reasoning | **AWS Bedrock** | **Claude Sonnet 4.6** | Classification, assessment, recommendation drafting |
| Alternate | **Azure OpenAI** | GPT-4o-class | Cross-check / fallback when Bedrock region unavailable |
| Alternate | **Google Vertex AI** | Gemini | Cost-optimized path for low-sensitivity bulk classification |

Model choice is **driven by the router**, not hard-coded into the agent. The
router selects a provider per request based on data sensitivity, latency budget,
and cost ceiling. That is the whole reason the project is multi-cloud: provider
independence is a *feature*, demonstrated, not a slogan.

> Default is Claude Sonnet 4.6 on Bedrock because it gives the best
> reasoning-per-dollar for a multi-step agent and is generally available to all
> Bedrock customers. Swapping the default is a config change, not a code change.

---

## Repository layout

```
custodian/
├── java-core/          Spring Boot control plane (governance, audit, approval, cost)
├── python-ai/          FastAPI AI plane (router, guardrails, RAG, agent)
├── docs/
│   ├── adr/            Architecture Decision Records — the "why" behind each choice
│   └── diagrams/       Architecture & sequence diagrams
└── deploy/             docker-compose for local end-to-end run
```

## Running locally

**Full step-by-step instructions are in [RUNNING.md](RUNNING.md).** It runs in stub mode with no cloud credentials and zero cost. Quick version:

```bash
# AI plane
cd python-ai && pip install -r requirements.txt && uvicorn app.main:app --reload

# Control plane
cd java-core && ./mvnw spring-boot:run

# or the whole thing
docker compose -f deploy/docker-compose.yml up
```

Set provider credentials via environment (see `python-ai/.env.example`). With no
credentials the AI service runs in **stub mode** so the full workflow, governance,
and audit trail are demonstrable without any cloud spend.

---

## What to read first

1. `docs/adr/0001-model-agnostic-routing.md` — why the router exists
2. `docs/adr/0002-human-in-the-loop-gating.md` — why nothing auto-commits
3. `docs/adr/0003-java-python-split.md` — why two languages
4. `python-ai/app/agent/assessment_agent.py` — the agent loop
5. `java-core/.../approval/ApprovalStateMachine.java` — the governance gate

## Tests

The governance guarantee is proven in executable form — run `mvn test` in `java-core/`. `ApprovalStateMachineTest` shows a high-risk recommendation can never reach `COMMITTED` without an explicit, named human approval.
