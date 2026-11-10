# ADR 0004 — Policy enforcement inside the Spring Boot control plane, not an external policy engine

## Status
Accepted for the reference implementation. Revisit before any enterprise deployment (see Migration path).

## Context
The control plane decides, per request, whether an assessment may proceed, which
sensitivity tier applies (and therefore which model route is allowed), and whether
the recommendation must wait at the human approval gate. That is policy. The
alternatives were to express it in Java inside the control plane, or to externalise
it to a dedicated engine such as Open Policy Agent (Rego), HashiCorp Sentinel or
Cedar.

The reference implementation has one deployment, one author and a small policy
set: tier by sensitivity, allowed providers per tier, approval triggers.

## Decision
Policy is evaluated in-process in the Java control plane, alongside the approval
state machine and the audit log, and is driven by configuration rather than
hard-coded values. The point where the decision is made is the seam at which an
external engine would be introduced.

## Rationale
- **Atomic decision plus audit.** The policy decision, the state transition and
  the audit event are written by the same component in the same request. With an
  external engine there are two decision logs to reconcile.
- **Debuggability.** One JVM, one debugger, one log stream. For a reference
  implementation reviewed by one person, every policy bug must be reproducible
  without a second runtime.
- **No network hop on the request path.**
- **Scope.** The policy set is small enough that a general-purpose policy
  language adds surface without removing complexity.

## Consequences
- Policy is written in Java, so risk and security teams cannot author or review
  it without a developer, and policy is versioned with application releases
  rather than independently.
- Bank-wide policies shared by many services cannot be reused by this component.
- This does not scale to an estate where policy is owned centrally.

## Migration path
Introduce an explicit `PolicyDecisionPoint` interface in the control plane and
provide an OPA implementation: Rego policies versioned in Git and served as
bundles, OPA running as a sidecar, decision logs shipped to the SIEM. The control
plane continues to own the approval state machine and the audit record; it sends
the input document (caller identity, tenant, sensitivity tier, requested
provider, action) to OPA and stores the decision ID on the audit event. Cedar
(AWS Verified Permissions) is the alternative where the estate standardises on
AWS. The Python AI plane is unchanged.

## Alternatives considered
- OPA from day one: the recommended enterprise target; rejected here on scope and
  debuggability.
- Sentinel: tied to the HashiCorp ecosystem; only sensible where Terraform
  Enterprise policy is already in use.
- Policy in the Python AI plane: rejected. Policy must be enforced before model
  traffic by the component that owns the audit record.
