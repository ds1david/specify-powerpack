# Cross-Spec Ownership Contract

This contract belongs to **SPEC-001A — Review Lineage, GPT Web Continuity and Reproducibility**.

## Ownership rule

Every functional PowerPack capability has exactly one normative owner specification or amendment chain.

Infrastructure specifications may expose reusable mechanisms consumed by capabilities, but they do not own capability-specific semantics unless they explicitly amend the capability owner.

```text
CAPABILITY OWNER
  -> states
  -> transitions
  -> gates
  -> evidence semantics
  -> failure semantics
  -> approval semantics
  -> capability-specific budgets
  -> provider/transport semantics

INFRASTRUCTURE OWNER
  -> registration
  -> generic setup/config storage
  -> generic state framework
  -> component lifecycle/coherence
  -> diagnostics plumbing
  -> capability registry

ORCHESTRATOR
  -> stage ordering
  -> handoff between capabilities
```

## Current authority map

| Specification | Normative responsibility |
|---|---|
| SPEC-001 | baseline product surface; initial preservation of `implement-review`; removal of legacy commands; implementation predecessor evidence |
| SPEC-001A / physical SPEC-004 | all `implement-review` review semantics, lifecycle and GPT Web continuity |
| SPEC-002 | generic PowerPack plugin infrastructure |
| SPEC-003 | `checklist-converge` capability semantics |
| later orchestration specs | ordering between stages/capabilities only |

## SPEC-002 reconciliation

For `implement-review`, SPEC-002 review-specific statements are subordinate to SPEC-001A.

The following SPEC-002 requirement ranges are specifically delegated to SPEC-001A where they define `implement-review` semantics:

```text
FR-021 .. FR-024
FR-032 .. FR-036
```

SPEC-002 may still provide generic configuration, environment discovery, state storage, registry and diagnostics used by `implement-review`.

Environment facts are infrastructure output. The meaning of those facts for `implement-review` readiness remains a SPEC-001A decision.

Example:

```text
SPEC-002 may report:
  codex_executable = true
  codex_authenticated = true
  github_connector_ready = true

SPEC-001A decides:
  implement_review_readiness = READY | BLOCKED_CONFIGURATION
```

## SPEC-003 reconciliation

SPEC-003 exclusively owns checklist-specific semantics.

Where SPEC-003 repeats generic persistence mechanics such as project-local JSON, atomic replacement, revision conflict detection or ENV non-authority, those requirements are compatibility constraints on `checklist-converge`; the reusable mechanism is owned by SPEC-002 when its shared infrastructure exists.

The following remain SPEC-003-specific and MUST NOT be generalized away:

```text
checklist item classification
REQUIRED / ADVISORY / IGNORED participation
before_checklist / after_checklist / before_tasks semantics
clarification behavior
TASKS_STALE behavior
checklist convergence budget / no-progress semantics
checklist-specific persisted fields
```

`checklist-converge` budget state and `implement-review` budget state are independent.

## Amendment rule

A later specification may change capability-specific semantics only when it states all of:

```text
Amends: <capability-owner-spec>
Affected capability: <capability-id>
Superseded clauses: <explicit requirement/section list>
Preserved clauses: <explicit scope>
```

Absent that declaration, later infrastructure and orchestration specs MUST consume the capability contract rather than redefine it.
