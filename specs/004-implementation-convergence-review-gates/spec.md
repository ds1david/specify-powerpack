# Feature Specification: Implementation Convergence and Review Artifact Gates

**Feature Branch**: `004-implementation-convergence-review-gates`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Preserve the natural Spec Kit flow where `speckit-implement` and `speckit-converge` are the same commands in initial and repair scenarios; make implementation convergence an explicit prerequisite for code review; persist findings and artifact evidence across sessions; never force review findings into `tasks.md`; and never execute a subsequent workflow phase without user consent."

## Overview

Add a PowerPack lifecycle contract for the post-task implementation path:

```text
speckit-specify <spec>
→ speckit-clarify <spec>
→ speckit-plan <spec>
→ speckit-checklist <spec>
→ speckit-checklist-converge <spec>
→ speckit-tasks <spec>
→ speckit-analyze <spec>
→ speckit-implement <spec>
→ speckit-converge <spec>
→ speckit-implement-review <spec>
```

`<spec>` is optional when repository context resolves exactly one active SPEC. The normal user experience MUST NOT require passing finding ids, review round ids or convergence origin flags to `implement` or `converge`.

The core problem is that implementation repair can be triggered by either convergence findings or review findings, while the user-facing commands remain identical:

```text
converge findings
      ↓
speckit-implement
      ↓
speckit-converge

review findings
      ↓
speckit-implement
      ↓
speckit-converge
```

`converge` MUST therefore be provenance-agnostic: it verifies the current implementation of the active SPEC and MUST NOT have a special "post-review" mode. The provenance of findings may be retained as evidence, but it is not a command-mode selector.

`implement-review` MUST be allowed only when the current implementation has an explicit fresh successful convergence attestation. Human prose is not sufficient evidence; the gate uses persisted structured state bound to the relevant SPEC and implementation snapshot.

## Relationship to Earlier Specifications

### SPEC-001 is frozen

SPEC-001 is already implemented and under PR review. **This specification MUST NOT modify any SPEC-001 artifact or redefine its historical acceptance criteria.**

If SPEC-001 establishes a baseline in which only `implement-review` is PowerPack-owned and upstream Spec Kit owns `speckit-implement` / `speckit-converge`, this SPEC MUST extend that accepted baseline through supported hooks, presets, extension/runtime adapters or other native Spec Kit composition. It MUST NOT rewrite SPEC-001 to make the new lifecycle appear retroactively required.

### SPEC-002 provides reusable infrastructure

When SPEC-002 infrastructure is available, this capability SHOULD reuse its capability registry, persistent JSON envelope, revision/freshness rules, diagnostics and native composition boundaries. This specification owns the post-implementation workflow semantics, not setup architecture.

### SPEC-003 remains a different convergence domain

SPEC-003 `checklist-converge` evaluates requirements-writing quality before task generation. This SPEC defines implementation convergence after `speckit-implement`.

These are separate gates:

```text
CHECKLIST CONVERGENCE
  authoritative target: requirements/checklist quality
  workflow location: before tasks

IMPLEMENTATION CONVERGENCE
  authoritative target: implementation vs accepted SPEC artifacts
  workflow location: after implement, before implement-review
```

A successful checklist-convergence state MUST NOT be treated as implementation convergence evidence, and vice versa.

## Architectural Decisions

### AD-001 — Commands remain provenance-agnostic

`speckit-implement` and `speckit-converge` are the same user-facing commands regardless of why the current work exists.

Forbidden command-mode design:

```text
speckit-implement --from-review
speckit-converge --review
speckit-converge --from-convergence
```

Equivalent optional explicit context MAY be provided by a user when useful, but it MUST NOT be required for normal workflow continuation.

### AD-002 — Active SPEC resolution is implicit by default

SPEC resolution precedence is:

```text
1. explicit SPEC supplied by the user
2. active SPEC resolved from repository context such as .specify/feature.json
3. fail closed when resolution is absent or ambiguous
```

Explicit context is an override/focus mechanism, not mandatory workflow plumbing.

### AD-003 — `tasks.md` remains planned work, not a review ledger

`tasks.md` is a Spec Kit planning artifact. Convergence/review findings are emergent obligations discovered after planning and MUST NOT be silently appended as generated tasks.

PowerPack SHALL persist findings separately with stable identity and source evidence.

### AD-004 — `implement` resolves actionable context automatically

After resolving the active SPEC, `implement` may consume:

```text
planned incomplete work from the SPEC task context
+ actionable convergence findings
+ actionable review findings
+ explicit user-supplied context/focus, if any
```

The user MUST NOT have to manually reconstruct prior findings to continue a normal repair loop.

A finding that is already resolved, superseded, dismissed or awaiting reviewer verification MUST NOT be presented as new implementation work unless a later authoritative state reopens it.

### AD-005 — Implementation evidence records the attempt, not self-approval

Completion of `implement` records or derives structured evidence for the implementation attempt. That evidence means only that implementation work occurred for the active SPEC/current repair context.

It MUST NOT imply convergence or review approval.

### AD-006 — `converge` evaluates the latest implementation, not its origin

`converge` resolves the active SPEC and the latest implementation evidence that has not been successfully converged for its current snapshot.

Its semantic question is always:

> Is this current implementation consistent with the accepted SPEC artifacts and configured convergence/quality rules?

It MUST NOT change evaluation behavior based on whether the implementation was motivated by `tasks.md`, a prior convergence finding, or a review finding.

### AD-007 — Convergence emits a structured attestation

A successful convergence MUST persist structured evidence conceptually containing:

```text
spec identity
implementation evidence identity
evaluated implementation snapshot/fingerprint
authoritative artifact fingerprints
convergence status
blocking finding count
quality/check results used by policy
recorded_at
```

The human-readable message `✅ Convergência concluída` is derived presentation; it is not the gate authority.

### AD-008 — Review requires current convergence

`implement-review` MUST fail closed unless the latest implementation has a fresh successful convergence attestation.

Conceptually:

```text
latest_implementation.id == convergence.implementation_id
AND
latest_implementation.snapshot == convergence.snapshot
AND
convergence.validity == FRESH
AND
convergence.status == CONVERGED
```

When false, the next recommended action is `speckit-converge`.

### AD-009 — Relevant changes stale convergence

Any relevant implementation change after successful convergence invalidates the prior convergence attestation for review. Changes to authoritative SPEC artifacts that affect the implementation contract also stale the attestation.

The review gate MUST NOT approve against stale convergence evidence.

### AD-010 — Findings preserve source and closure ownership without changing command semantics

A persisted finding MAY identify its source:

```text
CONVERGE
IMPLEMENT_REVIEW
```

and its closure authority. This is evidence/lifecycle metadata only.

A review finding MAY become implemented and converged, but final semantic closure remains owned by a later review round when the review protocol requires previous-finding validation.

A convergence finding MAY be closed by a later successful convergence when its condition is no longer present.

### AD-011 — Review findings flow to `implement`, never directly to `converge`

When `implement-review` returns `CHANGES_REQUIRED`, it persists actionable findings and stops.

The recommended sequence is:

```text
implement-review
  -> CHANGES_REQUIRED + findings
  -> STOP

user invokes speckit-implement
  -> implementation repair
  -> STOP

user invokes speckit-converge
  -> convergence evaluation
  -> STOP

user invokes speckit-implement-review
  -> reviewer validates current snapshot and prior findings
```

`implement-review` MUST NOT silently invoke `implement` or `converge`.

### AD-012 — Convergence findings use the same repair path

When convergence returns actionable findings:

```text
speckit-converge
  -> CONVERGENCE_REQUIRED + findings
  -> STOP

user invokes speckit-implement
  -> repair
  -> STOP

user invokes speckit-converge
  -> re-evaluate
```

No separate repair command is required.

### AD-013 — User invocation grants phase-local consent only

By default, invoking a workflow command authorizes only that phase.

Every command MUST:

```text
execute its own phase
→ persist its own state/evidence
→ report result
→ recommend next action
→ STOP
```

It MUST NOT execute the recommended next command automatically.

A separately selected orchestration/full-cycle capability MAY receive broader consent, but it MUST declare that scope explicitly and use bounded repair/no-progress budgets.

### AD-014 — Artifact gates are machine-readable

Consequential workflow transitions MUST use structured status/result codes and persisted evidence. Hooks, CLI adapters, agents and homologation scripts MUST NOT parse human prose to infer a successful gate.

### AD-015 — State survives sessions

Implementation/convergence/finding continuity required for this workflow MUST survive agent/session boundaries through project-local structured state/evidence. Environment variables are not cross-session authority.

### AD-016 — Evidence is linked, not duplicated into one mutable mega-record

The design SHOULD preserve causal linkage:

```text
SPEC artifacts
    ↓
implementation evidence
    ↓
convergence evidence
    ↓
review manifest / review round
    ↓
findings
    ↓
next implementation evidence
```

Each artifact may point to prior identities/digests instead of repeatedly copying entire historical payloads.

## Canonical State Flow

### Initial delivery

```text
TASKS/ANALYZE READY
      ↓ user
IMPLEMENT
      ↓
IMPLEMENTED / NEEDS_CONVERGENCE
      ↓ user
CONVERGE
      ├─ CONVERGENCE_REQUIRED
      │      ↓ findings persisted
      │     STOP
      │
      └─ CONVERGED
             ↓
            STOP
             ↓ user
IMPLEMENT-REVIEW
```

### Repair from convergence findings

```text
CONVERGENCE_REQUIRED
      ↓ findings
IMPLEMENTABLE
      ↓ user invokes implement
IMPLEMENTED
      ↓ user invokes converge
CONVERGED | CONVERGENCE_REQUIRED
```

### Repair from review findings

```text
IMPLEMENT-REVIEW
      ↓
CHANGES_REQUIRED
      ↓ review findings persisted
IMPLEMENTABLE
      ↓ user invokes implement
IMPLEMENTED
      ↓ user invokes converge
CONVERGED
      ↓ user invokes implement-review
prior review findings are dispositioned
```

The number of repair rounds is not semantically fixed. Individual automatic executions remain bounded and user-controlled.

## Artifact Gate Model

### G0 — Active SPEC gate

Applies to all SPEC-scoped phases.

**Allow when** exactly one active SPEC is resolved by explicit user selection or repository context.

**Block when** no SPEC or multiple conflicting SPECs are resolved.

**Suggested action**: select/provide the intended SPEC.

### G1 — Requirements/checklist gate before tasks

Owned primarily by SPEC-003 when its REQUIRED checklist participation policy applies.

**Allow when** required checklist-convergence state is fresh and non-blocking.

**Block when** required requirements-quality findings/clarifications remain.

**Suggested action**: checklist convergence or clarification according to the recorded state.

### G2 — Implementation evidence gate before converge

**Allow when** a current implementation attempt/evidence exists for the active SPEC and current relevant artifact context.

**Block when** no implementation evidence exists or the candidate evidence belongs to another SPEC.

**Suggested action**: `speckit-implement`.

`converge` does not require knowledge of why that implementation occurred.

### G3 — Convergence gate before implement-review

**Allow when** the latest implementation has a fresh `CONVERGED` attestation bound to the same implementation identity/snapshot.

**Block when** convergence is missing, stale, blocking or bound to an earlier implementation.

**Suggested action**: `speckit-converge`.

### G4 — Review snapshot gate

**Allow when** the immutable review manifest, repository HEAD/PR identity, implementation evidence and convergence evidence all refer to the same reviewable snapshot according to the active review protocol.

**Block when** identity/fingerprint evidence disagrees.

**Suggested action**: recompute the invalidated prerequisite phase; never silently approve.

### G5 — Previous-review-finding gate

On review round N+1, every still-relevant finding from prior review rounds MUST have an explicit disposition such as:

```text
RESOLVED
STILL_PRESENT
SUPERSEDED
INVALIDATED_BY_SCOPE_CHANGE
BLOCKED
```

Missing disposition blocks final approval.

### G6 — Consent gate

Transition recommendations are not execution authorization.

Unless broader orchestration consent was explicitly granted, every phase boundary stops and returns control to the user.

## Conceptual Evidence Models

Exact schemas/paths are plan decisions, but the following semantics are required.

### Implementation evidence

```json
{
  "schema_version": 1,
  "state_type": "implementation-evidence",
  "spec": "004-example",
  "implementation_id": "IMP-007",
  "snapshot": "sha256:...",
  "source_artifacts": [
    {"path": "specs/.../spec.md", "digest": "sha256:..."},
    {"path": "specs/.../tasks.md", "digest": "sha256:..."}
  ],
  "consumed_findings": ["REV-R03-F001", "CONV-R04-F001"],
  "status": "COMPLETED",
  "recorded_at": "<timestamp>"
}
```

`consumed_findings` is audit provenance. Its contents MUST NOT select a special converge mode.

### Convergence evidence

```json
{
  "schema_version": 1,
  "state_type": "implementation-convergence",
  "spec": "004-example",
  "convergence_id": "CONV-008",
  "implementation_id": "IMP-007",
  "snapshot": "sha256:...",
  "validity": "FRESH",
  "status": "CONVERGED",
  "blocking_findings": [],
  "checks": {
    "task_obligations": "PASS",
    "required_checklists": "PASS",
    "consistency": "PASS"
  },
  "recorded_at": "<timestamp>"
}
```

Task counts MUST be interpreted semantically. Historical/superseded markers MUST NOT block convergence merely because a raw completed-count is lower than a raw total when there are zero actionable unresolved obligations.

### Finding evidence

```json
{
  "id": "REV-R03-F001",
  "spec": "004-example",
  "source": "IMPLEMENT_REVIEW",
  "source_artifact": "<review-artifact-id-or-path>",
  "status": "OPEN",
  "closure_owner": "IMPLEMENT_REVIEW",
  "fingerprint": "sha256:..."
}
```

Findings are not automatically represented as new Spec Kit tasks.

## User Scenarios & Testing

### User Story 1 — Run implementation naturally without finding arguments (Priority: P1)

A user invokes `speckit-implement` with no special repair flags after either convergence or review findings.

**Acceptance Scenarios**:

1. Explicit SPEC is optional when `.specify/feature.json` or equivalent repository context resolves one active SPEC.
2. Open actionable findings for that SPEC are discovered automatically.
3. The user may provide explicit context to focus the implementation but is not required to repeat persisted finding ids.
4. No finding from another SPEC is consumed.
5. No convergence receipt is required merely to enter repair implementation.

### User Story 2 — Converge the latest implementation without origin modes (Priority: P1)

A user invokes the same `speckit-converge` command after initial implementation, convergence repair or review repair.

**Acceptance Scenarios**:

1. The command identifies the latest current implementation evidence for the active SPEC.
2. Evaluation rules are identical regardless of finding provenance.
3. No `--review`/`--from-review` mode is needed.
4. Successful convergence persists a structured attestation bound to the implementation snapshot.
5. Human summary output is derived from structured results.

### User Story 3 — Block review until implementation is explicitly converged (Priority: P1)

A user attempts `speckit-implement-review` immediately after an implementation change.

**Acceptance Scenarios**:

1. Missing convergence evidence blocks review.
2. Convergence for an older implementation blocks review.
3. Convergence for another SPEC blocks review.
4. Stale convergence after implementation/artifact mutation blocks review.
5. The response recommends `speckit-converge` without invoking it.
6. A fresh `CONVERGED` attestation for the current snapshot allows the review prerequisite to proceed.

### User Story 4 — Repair convergence findings without modifying tasks (Priority: P1)

`converge` detects implementation issues and emits findings.

**Acceptance Scenarios**:

1. Findings are persisted outside `tasks.md`.
2. `converge` stops after reporting `CONVERGENCE_REQUIRED`.
3. Later plain `speckit-implement` discovers the findings automatically.
4. A subsequent plain `speckit-converge` re-evaluates the resulting implementation.
5. The original planned tasks file is not polluted with synthetic repair tasks.

### User Story 5 — Repair review findings through the same implement/converge path (Priority: P1)

`implement-review` detects defects in a converged snapshot.

**Acceptance Scenarios**:

1. Review persists findings and returns `CHANGES_REQUIRED`.
2. Review does not invoke implementation automatically.
3. Plain `speckit-implement` consumes the applicable open review findings.
4. Plain `speckit-converge` evaluates the new implementation without a review-specific mode.
5. A new review round validates prior review findings before approval.

### User Story 6 — Preserve user consent at every phase boundary (Priority: P1)

A user wants to control whether the workflow proceeds after each phase.

**Acceptance Scenarios**:

1. `implement` never invokes `converge` by default.
2. `converge` never invokes `implement` or `implement-review` by default.
3. `implement-review` never invokes `implement` or `converge` by default.
4. Every successful/blocking result exposes a recommended next action when one is deterministic.
5. A separately selected orchestration mode may broaden authority only after explicit user consent.

### User Story 7 — Resume repair in a later session (Priority: P1)

A review or convergence finding is generated in one session and implementation continues later.

**Acceptance Scenarios**:

1. The later session reloads project-local structured state/evidence.
2. No previous-process ENV is required.
3. State is checked for SPEC identity and freshness before use.
4. Stale/malformed state cannot silently authorize review.

### User Story 8 — Handle historical partial tasks correctly (Priority: P1)

A task artifact contains a historical partial marker that has been superseded by later explicit work/evidence.

**Acceptance Scenarios**:

1. Raw checkbox totals alone do not determine convergence.
2. Zero actionable open work plus explicit supersession evidence may still converge.
3. An actually unresolved partial task remains blocking.
4. The convergence report explains the distinction in machine-readable facts and human-readable summary.

## Functional Requirements

- **FR-001**: Preserve the canonical workflow `specify → clarify → plan → checklist → checklist-converge → tasks → analyze → implement → converge → implement-review`.
- **FR-002**: SPEC-001 artifacts MUST remain unchanged by this capability.
- **FR-003**: Explicit SPEC arguments are optional when exactly one active SPEC can be resolved from repository context.
- **FR-004**: Ambiguous or missing SPEC context MUST fail closed.
- **FR-005**: `speckit-implement` MUST use the same user-facing command for initial work and all repair work.
- **FR-006**: `speckit-converge` MUST use the same user-facing command after every implementation attempt.
- **FR-007**: Normal repair flow MUST NOT require user-supplied finding ids or provenance flags.
- **FR-008**: Explicit user context MAY focus/override implicit context when the user chooses.
- **FR-009**: Review/convergence findings MUST NOT be automatically appended to `tasks.md`.
- **FR-010**: Findings MUST have persistent stable identity, SPEC identity, source evidence and lifecycle status.
- **FR-011**: `implement` MUST resolve actionable findings for the active SPEC automatically.
- **FR-012**: `implement` MUST NOT require convergence as a prerequisite for repair execution.
- **FR-013**: Implementation completion MUST produce or derive structured implementation evidence distinct from convergence/review approval.
- **FR-014**: `converge` MUST require current implementation evidence for the active SPEC.
- **FR-015**: `converge` semantics MUST NOT branch based on whether implementation inputs originated from tasks, convergence findings or review findings.
- **FR-016**: Successful `converge` MUST persist a structured convergence attestation bound to implementation identity/snapshot and authoritative artifact fingerprints.
- **FR-017**: `implement-review` MUST require a fresh successful convergence attestation for the latest implementation.
- **FR-018**: Relevant implementation changes after convergence MUST stale prior convergence evidence.
- **FR-019**: Relevant authoritative SPEC-artifact changes after convergence MUST stale prior convergence evidence.
- **FR-020**: Stale/missing/mismatched convergence MUST block review and recommend `speckit-converge`.
- **FR-021**: Review/convergence gates MUST consume machine-readable state; human prose MUST NOT be parsed as authoritative gate state.
- **FR-022**: Review findings MUST be persisted before returning `CHANGES_REQUIRED`.
- **FR-023**: Convergence findings MUST be persisted before returning `CONVERGENCE_REQUIRED`.
- **FR-024**: A later review round MUST disposition all still-relevant findings from prior review rounds before final approval.
- **FR-025**: Finding provenance MAY be retained for audit but MUST NOT select different `implement` or `converge` command semantics.
- **FR-026**: Each normal command invocation MUST stop at its own phase boundary after reporting/recommending the next action.
- **FR-027**: Automatic execution of another workflow phase requires separately explicit user consent/orchestration authority.
- **FR-028**: Any autonomous orchestration loop MUST be bounded by configured repair/no-progress budgets and MUST return control when exhausted.
- **FR-029**: Required workflow state MUST survive sessions through project-local structured persistence, not shell/global ENV.
- **FR-030**: Cross-session consumers MUST validate schema, SPEC identity, freshness and artifact/snapshot identity before consequential use.
- **FR-031**: Checklist-convergence evidence from SPEC-003 MUST NOT satisfy implementation-convergence gate G3.
- **FR-032**: Implementation-convergence evidence MUST NOT be used as requirements-quality checklist-convergence proof.
- **FR-033**: Historical/superseded task markers MUST be distinguished from actionable unresolved work; raw task totals alone MUST NOT determine convergence.
- **FR-034**: The review manifest and convergence evidence MUST identify the same current reviewable snapshot according to the active review protocol.
- **FR-035**: A mismatch among active SPEC, implementation evidence, convergence evidence and review snapshot MUST fail closed.
- **FR-036**: Machine-readable outputs MUST expose deterministic status/reason/recommended-action fields suitable for hooks, agents and homologation automation.

## Success Criteria

- **SC-001**: Contract tests demonstrate that initial implementation, convergence repair and review repair all use the same `speckit-implement` entry point.
- **SC-002**: Contract tests demonstrate that all three implementation origins use the same `speckit-converge` entry point with no provenance mode flag.
- **SC-003**: 100% of review attempts without a fresh current convergence attestation fail closed before material review execution.
- **SC-004**: A stale convergence fixture created by changing implementation after convergence is rejected in 100% of tests.
- **SC-005**: A convergence receipt for another SPEC or older implementation never satisfies the review gate.
- **SC-006**: Review/convergence repair loops create zero automatic synthetic entries in `tasks.md`.
- **SC-007**: A finding persisted in one session is discoverable by a later plain `speckit-implement` invocation after validation.
- **SC-008**: Prior review findings are never silently dropped on later review approval.
- **SC-009**: Every normal phase terminates without invoking its recommended next phase unless orchestration consent is explicitly active.
- **SC-010**: Fixtures with superseded historical partial task markers can converge when zero actionable obligations remain, while genuinely unresolved partial work blocks.
- **SC-011**: Human-readable convergence summaries can be regenerated from structured convergence evidence without being parsed back as workflow authority.
- **SC-012**: Linux/WSL and Windows homologation can assert all gates from machine-readable results without shell-specific persistent ENV.

## Assumptions

- The accepted SPEC-001 implementation may use upstream Spec Kit `speckit-implement` and `speckit-converge`; this SPEC will extend rather than rewrite that baseline.
- Native Spec Kit composition/hooks/presets or equivalent supported extension points can observe or bracket workflow phases sufficiently to persist PowerPack evidence without forking upstream skills.
- `.specify/feature.json` or equivalent supported repository context can identify the active feature/SPEC in normal usage.
- `implement-review` already has or will retain immutable snapshot/review evidence capable of linking to convergence evidence.
- Exact state paths, schemas, hashing algorithm inputs and hook mechanics are technical-plan decisions.

## Non-Goals

- Modifying SPEC-001 or changing its review acceptance criteria.
- Replacing upstream Spec Kit `implement`/`converge` with separate repair commands solely for PowerPack.
- Adding `--from-review`, `--review`, or equivalent mandatory provenance modes.
- Converting every review/convergence finding into a Spec Kit task.
- Letting `implement` self-certify convergence.
- Letting `converge` self-certify independent code-review approval.
- Treating a checklist-convergence receipt as implementation-convergence evidence.
- Automatically running the next phase after a normal command without explicit broader user consent.
- Defining the exact persistence/storage implementation before planning.

## Core Invariants

```text
SPEC-001 == FROZEN_HISTORICAL_CONTRACT
```

```text
IMPLEMENT_COMMAND(initial) == IMPLEMENT_COMMAND(converge_repair) == IMPLEMENT_COMMAND(review_repair)
```

```text
CONVERGE_COMMAND(initial) == CONVERGE_COMMAND(converge_repair) == CONVERGE_COMMAND(review_repair)
```

```text
finding_origin != command_mode
```

```text
review_or_converge_finding != automatic_tasks_md_entry
```

```text
IMPLEMENT
  != requires_previous_convergence
```

```text
IMPLEMENT_REVIEW
  => latest_implementation_has_fresh_CONVERGED_attestation
```

```text
implementation_changed_after_convergence
  => convergence_validity == STALE
  => implement_review == BLOCKED
```

```text
CHECKLIST_CONVERGENCE != IMPLEMENTATION_CONVERGENCE
```

```text
command_invocation
  => authority_for_current_phase_only
  != authority_for_recommended_next_phase
```

```text
HUMAN_SUCCESS_MESSAGE != MACHINE_GATE_AUTHORITY
```
