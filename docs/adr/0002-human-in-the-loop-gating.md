# ADR 0002 — Human-in-the-loop gating

## Status
Accepted

## Context
An architecture-modernization recommendation can carry significant blast radius:
breaking a shared database or resequencing a migration affects live financial
systems. A model must not be able to auto-commit such a decision.

## Decision
Every recommendation carries a `risk_score`. Above a configurable threshold the
**approval state machine** moves to `PENDING_APPROVAL` and the recommendation can
only reach `COMMITTED` via an explicit, audited human action. The only
side-effecting transition (`commit`) is guarded so it is unreachable from any
state except `APPROVED`.

## Consequences
- The agent is safe to run in a regulated environment because nothing
  irreversible happens without a named human.
- Low-risk recommendations still auto-approve, so the gate does not become
  bureaucratic friction for trivial changes.
- The approver identity is mandatory and audited, satisfying accountability and
  traceability requirements.
