# ADR 0005 — Direct provider calls in the AI plane rather than an agent framework

## Status
Accepted for the reference implementation. Framework adoption is a supported
option (see Adoption path).

## Context
The Python AI plane routes calls across Bedrock, Vertex AI and Azure OpenAI,
applies guardrails, retrieves grounding and runs a fixed multi-step assessment
(classify, retrieve, assess, recommend). Frameworks such as LangChain, LangGraph
and the Microsoft Agent Framework offer prebuilt chains, memory, tool abstractions
and tracing integrations.

## Decision
The AI plane calls provider SDKs directly through its own `ModelRouter`, and the
agent loop is explicit, hand-written Python. No agent framework is a runtime
dependency.

## Rationale
- **Governance is the product.** Every step on the request path (redaction,
  routing decision, model call, grounding, recommendation) must be visible to,
  and recorded by, Custodian. A framework's internal loop hides steps that a
  control function needs to inspect.
- **The trace must equal the execution.** `AssessmentResult.record()` captures
  each step and its output; hand-written orchestration guarantees that what is
  audited is what ran.
- **Small, pinned dependency surface.** Agent frameworks change quickly and
  bring large transitive trees. For a component on the path to sensitive data,
  a short requirements file is easier to assure.
- **No framework overhead on the hot path.**
- **Portability.** Organisations standardise on different frameworks; a
  framework-free core can be wrapped by whichever one is mandated.

## What this costs
- Conversation memory, long-context summarisation and generic tool-calling are
  not provided by a library. The current agent is a fixed pipeline with no
  conversational memory; adding it is Custodian code to own.
- No out-of-the-box tracing integration (LangSmith and similar). The plane
  currently records steps in the result object; OpenTelemetry spans are the
  planned production replacement.
- No prebuilt tool wrappers; tools are declared explicitly (MCP servers or
  functions).

## Consequences
- Full visibility and control of every step; minimal dependencies; portable.
- More code to own as orchestration patterns grow.

## Adoption path
If a framework is mandated, LangGraph (or the Microsoft Agent Framework) becomes
the orchestration layer while Custodian remains the policy, identity, redaction
and audit layer: the framework's model step is pointed at `ModelRouter` and its
tool step at Custodian's tool invoker. Governance stays outside the framework,
which is the property that matters.

## Alternatives considered
- LangChain: rejected for the core; its chain abstractions impose a step model
  and obscure the trace.
- LangGraph: closest fit for explicit state machines; deferred to the adoption
  path.
- Microsoft Agent Framework: appropriate for Azure-centric estates; same
  adoption path.
