# ADR 0006 — REST (HTTP/JSON) between the control plane and the AI plane rather than gRPC

## Status
Accepted. gRPC is retained as a documented option for the internal path.

## Context
The Java control plane calls the Python AI plane on every assessment. gRPC
(HTTP/2, protobuf, streaming) has lower per-call overhead than REST over JSON.
Agentic workloads can be latency-sensitive.

## Decision
The plane-to-plane contract is REST, exposed by FastAPI and described by
OpenAPI. The contract is narrow (a single `/assess` call, see ADR 0003).

## Rationale
- **Composability with the estate.** The interface is meant to sit behind an API
  gateway and to be composed through GraphQL federation (Apollo) where an
  organisation stitches AI capabilities together with other services. REST with
  an OpenAPI contract is what those layers consume natively.
- **Operability.** REST is inspectable with standard tooling, WAF-friendly, and
  trivially mocked in tests; every API gateway, mesh and observability stack in
  a bank handles it without special configuration.
- **Where the latency is.** The model call dominates end-to-end time (hundreds
  of milliseconds to seconds). The plane-to-plane hop is single-digit
  milliseconds; moving it to gRPC removes a small fraction of total latency.
- **Contract governance.** OpenAPI contracts are reviewable and reusable by
  architecture governance; proto definitions are less familiar to most bank API
  governance functions.

## Consequences
- Higher per-call overhead and larger payloads than gRPC; weaker bidirectional
  streaming.
- At very high request rates with sub-10 ms budgets the REST hop becomes a
  measurable cost.

## When to switch
If profiling shows the plane-to-plane hop above roughly 10% of end-to-end
latency, or a deployment needs bidirectional streaming for tool loops, introduce
gRPC for that internal path only and keep the REST/OpenAPI surface at the edge.

## Alternatives considered
- gRPC from the start: rejected on composability and operability.
- GraphQL between planes: rejected; GraphQL is the composition layer at the
  edge, not the internal transport.
