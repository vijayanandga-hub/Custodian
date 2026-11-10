# ADR 0007 — In-memory stores for the reference implementation; PostgreSQL with pgvector as the production target

## Status
Accepted. The in-memory implementation is deliberate for the demo; the
production target is specified here so the interfaces are built to it.

## Context
Custodian persists four kinds of data: approval state (each request's state
machine), the audit trail (append-only record of every decision and model call),
cost metering (spend per tenant) and retrieval embeddings for grounding.

Today, in this repository:
- approval state and tenant maps live in `ConcurrentHashMap` in the orchestrator;
- the audit log is an append-only `CopyOnWriteArrayList` (`AuditLog`), with no
  update or delete operation exposed;
- cost metering is a `ConcurrentHashMap` of `DoubleAdder` per tenant;
- retrieval is an in-memory cosine-similarity store over a small curated corpus
  with a deterministic hashing embedding, so the demo runs offline with no
  network and no database.

## Decision
Keep the in-memory stores for the reference implementation, behind the existing
interfaces (`AuditLog`, `CostMeter`, `PatternRetriever.retrieve`), and define the
production target as **a single PostgreSQL database** holding approval state,
audit and metering in relational tables and embeddings in **pgvector** (HNSW),
with audit immutability enforced by an insert-only database role.

## Rationale for the production target
- **Transactional integrity.** A policy decision, its state transition and its
  audit row must commit together. That is natural in one relational database
  and awkward across two stores.
- **Audit is relational.** Internal audit asks "every write-tier action by agent
  X in period Y with its approver". SQL answers that directly; a document or
  vector store does not.
- **The vector index is sensitive data.** Embeddings carry the sensitivity of
  the text they were built from (embedding inversion recovers meaningful content
  from vectors), so the index must sit under the same residency, encryption and
  access controls as the source. One governed database makes that one control.
- **Operational simplicity.** One backup, one encryption-at-rest configuration,
  one credential set, one HA story; banks already run PostgreSQL (RDS or Aurora
  PostgreSQL) under existing controls.
- **Adequate retrieval performance.** For corpora in the tens of millions of
  vectors, pgvector with HNSW is well within the latency budget of a request the
  model call dominates. (pgvector 0.8 with HNSW on PostgreSQL 16 has been
  validated separately for this purpose.)

## Rationale for keeping in-memory in the demo
- The repository must run with no external services so a reviewer can execute
  the governance flow end to end in minutes.
- The interfaces are the seam; swapping the backend is isolated to the store
  classes and the retriever module.

## Consequences
- The demo loses all state on restart and is single-instance only. This is
  acceptable for a reference implementation and unacceptable for anything else.
- The production target needs time-partitioning of the audit table, archival of
  closed partitions to object storage with retention, and read replicas for
  analytics.
- At very large retrieval scale, embeddings can move to OpenSearch or a managed
  vector service while audit and state remain in PostgreSQL.

## Alternatives considered
- Dedicated vector database plus PostgreSQL: two stores to govern for sensitive
  data and no transactional link; rejected as the default.
- Document store (MongoDB, DynamoDB) for audit: audit queries are relational and
  immutability is easier to enforce with SQL role permissions; rejected.
- Kafka as the audit log: useful as an additional sink to the SIEM, not as the
  system of record; deferred.
