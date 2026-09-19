# SPEC-002 Responsibility Boundary Clarification

This clarification is added by SPEC-001A to remove cross-spec ownership ambiguity without rewriting SPEC-001 history.

## Normative boundary

SPEC-002 owns **generic PowerPack infrastructure**:

```text
native bundle / extension / preset composition
capability registry
setup and reconfiguration engine
generic configuration persistence
generic project-local state framework
component coherence
installation/capability diagnostics
machine-readable doctor/status plumbing
environment capability discovery
```

SPEC-002 does **not** own `implement-review` capability semantics.

`implement-review` semantics are owned exclusively by the SPEC-001 -> SPEC-001A amendment chain.

## Review-specific clauses

Where the SPEC-002 draft defines review-specific behavior, the following clauses are delegated to SPEC-001A and MUST NOT be treated as competing authority for `implement-review`:

```text
FR-021 .. FR-024
FR-032 .. FR-036
```

This includes:

- executor/topology/evidence-backend meaning for `implement-review`;
- GPT Web / ChatGPT Project activation semantics for `implement-review`;
- review rounds and round budget;
- previous-finding accounting;
- snapshot approval invalidation;
- budget-exhaustion semantics;
- final approval semantics.

SPEC-002 may still expose generic facts required by the capability, such as executable/authentication/connector/component readiness. SPEC-001A decides how those facts map to `implement-review` readiness and failure state.

## No capability-semantic branching in infrastructure

The setup engine, registry, state framework and doctor SHOULD consume a capability descriptor/contract rather than encode `implement-review`-specific lifecycle decisions.

Conceptually:

```text
SPEC-002 infrastructure
    -> discovers facts
    -> stores generic config/state
    -> invokes capability readiness/status contracts

SPEC-001A implement-review
    -> interprets review-specific facts
    -> owns review state machine
```

A future change to `implement-review` semantics requires an explicit amendment to SPEC-001A, not a silent change to SPEC-002 infrastructure.
