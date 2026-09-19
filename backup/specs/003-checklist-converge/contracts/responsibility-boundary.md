# SPEC-003 Responsibility Boundary Clarification

This clarification is added by SPEC-001A to remove cross-spec ownership ambiguity.

## Normative boundary

SPEC-003 exclusively owns `checklist-converge` capability semantics, including:

```text
checklist item classifications
REQUIRED / ADVISORY / IGNORED participation
before_checklist / after_checklist / before_tasks behavior
requirements-only repair boundaries
clarification / blocked-decision semantics
TASKS_STALE behavior
checklist-specific state fields
checklist convergence budget and no-progress semantics
```

SPEC-003 does not own `implement-review` semantics.

Those semantics are owned by the SPEC-001 -> SPEC-001A amendment chain.

## Generic infrastructure reuse

Where SPEC-003 repeats generic persistence rules such as:

```text
project-local JSON authority
schema/revision metadata
atomic replacement
revision conflict detection
cross-session reload
ENV not being durable authority
```

those statements constrain `checklist-converge` compatibility, but the reusable generic mechanism belongs to SPEC-002 when SPEC-002 shared infrastructure is available.

SPEC-003 retains ownership of checklist-specific schema fields and state transitions.

## Independent budgets

```text
checklist_converge_budget
  != implement_review_round_budget
```

The two counters, exhaustion states and no-progress semantics are independent unless a future orchestration specification explicitly coordinates them without redefining either capability's internal contract.

## Future infrastructure migration

Migrating checklist state to shared SPEC-002 infrastructure MUST preserve SPEC-003 user-visible semantics. Such a migration is infrastructure reuse, not a transfer of capability ownership.
