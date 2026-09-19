# SPEC-003 Contract — No-Assumptions Checklist Acceptance

This contract is normative for SPEC-003 checklist convergence.

## Core rule

`checklist-converge` MUST NOT infer that an item is required now, satisfied, deferred, not applicable, acceptable for an MVP, or outside the current phase.

Every consequential checklist item MUST be evaluated individually against one explicit delivery target:

```text
FULL_SPEC | CURRENT_PHASE | MVP_MIN | MVP_MAX
```

The target and item membership MUST come from authoritative artifacts or an explicit user/product decision.

## Per-item target disposition

Every managed checklist item receives exactly one target disposition:

```text
REQUIRED_NOW
EXPLICITLY_DEFERRED
NOT_APPLICABLE_WITH_REASON
```

For `EXPLICITLY_DEFERRED`, the state MUST cite the authoritative source of the deferral and destination phase/MVP/future SPEC when known.

For `NOT_APPLICABLE_WITH_REASON`, the state MUST record concrete applicability evidence. Missing implementation or reviewer preference is not applicability evidence.

If target membership is ambiguous, the result is:

```text
CLARIFICATION_REQUIRED | BLOCKED_DECISION
```

never an inferred disposition.

## Per-item semantic acceptance

Each `REQUIRED_NOW` checklist item MUST be analyzed and accepted explicitly. It may be marked satisfied only when existing authority and evidence prove the requirement-quality condition for the selected target.

A reviewer MUST NOT mark an item `[x]` because:

- the requirement seems reasonable;
- implementation exists;
- tests pass;
- a similar item was accepted;
- the item appears optional;
- the PR title says MVP;
- the reviewer believes later phases will cover it;
- the implementation is "good enough" for the current stage.

## Delivery-target semantics

### FULL_SPEC

Every applicable checklist obligation for the active SPEC is `REQUIRED_NOW` unless there is authoritative proof of non-applicability.

### CURRENT_PHASE

Only items explicitly assigned to the named current phase may be evaluated as phase-required. Later-phase items remain visible as `EXPLICITLY_DEFERRED` with authority.

### MVP_MIN

Only explicitly declared minimum-MVP membership is required. Priority labels alone do not define MVP membership.

### MVP_MAX

Every item explicitly included in the maximum intended MVP/release slice is required. The reviewer MUST NOT shrink or expand that boundary.

## Convergence behavior

For every `REQUIRED_NOW` item:

```text
SATISFIED
RESOLVABLE_GAP
BLOCKED_DECISION
INVALIDATED
STRUCTURAL_GAP
```

remain semantic classifications from SPEC-003, but they MUST be interpreted inside the selected target.

`RESOLVABLE_GAP` may be repaired only from existing authority. Missing new intent must block/clarify.

## State requirements

Persistent checklist JSON MUST carry enough information to reconstruct the decision without session memory or ENV, including at least:

```text
delivery target mode/name
target authority/fingerprint
checklist path
item id/fingerprint
target disposition
disposition authority/reason
semantic classification
evidence/reason
validity
```

A target membership or authoritative-source change makes affected prior decisions stale.

## Gate rules

`before_tasks` MUST enforce REQUIRED checklist obligations only after target membership and item dispositions are validated.

It MUST NOT:

- block on an explicitly deferred item;
- allow a required item because the reviewer assumes it is future work;
- convert an unresolved required item into technical debt merely to proceed;
- treat a stale target decision as fresh.

## Required tests

The implementation MUST prove at least:

1. an item with ambiguous phase/MVP membership blocks for clarification;
2. an explicitly later-phase item is visible but does not block `CURRENT_PHASE`;
3. priority labels alone cannot create `MVP_MIN` or `MVP_MAX` membership;
4. each required item has an individual disposition, semantic classification and evidence record;
5. an item cannot be marked satisfied from application code/tests alone;
6. changed target authority invalidates the prior item decision;
7. cross-session consumers recover the same target/item decisions from JSON without ENV;
8. unresolved required items cannot be bypassed through technical-debt/backlog disposition.
