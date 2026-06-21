# ADR 0003 — Java control plane, Python AI plane

## Status
Accepted

## Context
The system has two distinct concerns: enterprise governance (integration, audit,
approval, cost accounting) and AI mechanics (routing, guardrails, retrieval,
the agent loop). These have different ecosystems and different change rates.

## Decision
Split along that seam. The **control plane is Spring Boot (Java)** — the
system-of-record, where governance and integration depth live. The **AI plane is
FastAPI (Python)** — where the model SDKs, guardrail tooling, and retrieval
ecosystem live. They communicate over internal REST. The Java core owns the
request lifecycle; the Python service is a stateless capability it calls.

## Consequences
- Each plane uses the idiomatic stack for its job and can scale independently.
- One internal network hop is introduced; mitigated by colocating the services
  and keeping the contract narrow (a single `/assess` call).
- Clear ownership boundary: governance correctness is provable in the JVM,
  independent of model behaviour.
