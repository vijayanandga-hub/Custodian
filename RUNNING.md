# Running Custodian locally

Custodian has two services: a **Python AI plane** (FastAPI) and a **Java control
plane** (Spring Boot). By default the AI plane runs in **stub mode** — model calls
return deterministic canned responses, so the entire workflow (routing,
guardrails, RAG, audit, and the human-approval gate) runs end-to-end with **no
cloud credentials and zero cost**. Add real provider credentials only when you
want live model calls (see the last section).

Run Part 1 first, then Part 2.

## Prerequisites

- Python 3.10+  (`python --version`)
- Java 21+  (`java -version`)
- Maven  (`mvn -version`)

---

## Part 1 — Python AI plane (port 8000)

From the repository root:

```bash
cd python-ai
python -m venv .venv

# activate the virtual environment:
#   Windows:  .venv\Scripts\activate
#   macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Leave this terminal running. Verify in a second terminal:

```bash
curl -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -d '{"component_description":"Legacy PaymentProcessor, Java/Spring, writes to a shared CORE_TXN database, synchronous calls to fraud, ledger and notification."}'
```

Expected: JSON with the agent steps (classification routed to Gemini, assessment
routed to Claude), a recommendation with a `risk_score`, the metered
`total_cost_usd`, and `needs_human_approval: true`.

Or open `http://localhost:8000/docs` for the interactive FastAPI page and use
"Try it out" on `/assess`.

---

## Part 2 — Java control plane (port 8080)

In a separate terminal, from the repository root:

```bash
cd java-core
mvn spring-boot:run
```

(First run downloads dependencies — give it a minute.) Leave it running. The
control plane calls the AI plane on port 8000 automatically.

Verify the full governed flow:

```bash
# 1) Submit a high-risk component
curl -X POST http://localhost:8080/api/assessments \
  -H "Content-Type: application/json" -H "X-Tenant-Id: acme-bank" \
  -d '{"componentDescription":"Legacy PaymentProcessor, Java/Spring, writes to shared CORE_TXN DB, synchronous fan-out to fraud/ledger/notification."}'
```

This returns a `correlationId` and `state: PENDING_APPROVAL` — the risk was high,
so the gate tripped and nothing auto-committed. Copy the `correlationId`, then:

```bash
# 2) A named human approves
curl -X POST http://localhost:8080/api/assessments/<correlationId>/approve \
  -H "X-Approver-Id: jane.architect"
```

This returns `state: COMMITTED`. That is the whole point of the system: the AI
produced a recommendation, the platform refused to auto-commit a high-risk
change, and it committed only after a named human approved — every step audited.

A convenience script doing both calls lives at `deploy/demo.sh`.

---

## Running with real models (optional)

Stub mode needs no credentials. To make live calls, copy `python-ai/.env.example`
to `python-ai/.env` and fill in any provider you have:

- **AWS Bedrock** (default reasoning model, Claude Sonnet 4.6): `AWS_REGION`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — your account must have Bedrock
  model access enabled for the Claude model.
- **Azure OpenAI** (fallback): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`.
- **Vertex AI** (cost-optimized path): `GCP_PROJECT`, `GCP_LOCATION`.

Any provider left blank simply stays in stub mode; the router still works and
falls through to whatever is configured. You never need all three — configuring
Bedrock alone exercises the default reasoning path with a real model.
