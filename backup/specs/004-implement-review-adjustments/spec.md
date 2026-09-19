# Feature Specification: Deterministic Implement Review Acceptance

**Feature Branch**: `004-implement-review-adjustments`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Adjust implement-review so PR reviews make no scope assumptions, bind implementation evidence to the active SPEC, evaluate every applicable requirement explicitly, distinguish defects from improvement proposals and verification gaps, and judge completion against an explicit delivery target: full SPEC, current phase, minimum MVP or maximum MVP."

## Overview

Strengthen `speckit-implement-review` without changing its core purpose: it remains the PowerPack implementation-quality gate for an implementation already produced by upstream Spec Kit.

This specification addresses two classes of weakness discovered while reviewing the SPEC-001 implementation:

1. **evidence can be technically present without proving the intended same-SPEC fact**; and
2. **a reviewer can accidentally infer delivery scope**, treating missing work as acceptable because it "looks like an MVP", or treating intentionally phased work as a defect because it "looks incomplete" against the whole specification.

The adjusted review contract is deterministic:

```text
RESOLVE ACTIVE SPEC
  -> RESOLVE EXPLICIT DELIVERY TARGET
  -> BUILD REQUIREMENT/ACCEPTANCE MATRIX
  -> PROVE SAME-SPEC IMPLEMENTATION EVIDENCE
  -> RUN CONVERGENCE + QUALITY GATES
  -> REVIEW EVERY APPLICABLE TARGET ITEM
  -> CLASSIFY FINDINGS / VERIFICATION GAPS / PROPOSALS
  -> APPROVE ONLY THE SELECTED TARGET
```

No stage may silently infer that a requirement is included, excluded, satisfied, deferred, not applicable, or "good enough".

## Relationship to SPEC-001

SPEC-001 intentionally reduced the PowerPack functional surface to `implement-review` and re-based its initial implementation prerequisite from a PowerPack receipt onto repository evidence.

This SPEC preserves that architectural decision. It does **not** restore the removed `speckit.implement` wrapper or its completion receipt.

It tightens the evidence contract so repository evidence proves the active SPEC rather than merely proving that some code changed somewhere on the branch.

## Relationship to SPEC-003

SPEC-003 (`checklist-converge`) and this SPEC share one semantic rule:

> scope is never inferred.

Both capabilities use an explicit delivery target and item-by-item disposition. Checklist convergence applies that rule to requirements-quality checklist items; implement-review applies it to implementation, acceptance evidence and PR findings.

The implementations MAY share a common target/disposition schema if shared PowerPack state infrastructure exists, but neither SPEC depends on the other being implemented first.

## Terminology

### Delivery target

Exactly one delivery target MUST be selected for a consequential review verdict:

- `FULL_SPEC`: all applicable requirements and success criteria of the active SPEC are required now.
- `CURRENT_PHASE`: only requirements explicitly assigned by authoritative artifacts or an explicit user/product decision to the named current phase are required now.
- `MVP_MIN`: only the explicitly defined minimum viable acceptance set is required now.
- `MVP_MAX`: the explicitly defined maximum scope intended for the current MVP/release slice is required now; work explicitly beyond that boundary may remain deferred.

These labels are **not heuristics**. A reviewer MUST NOT invent the membership of a phase or MVP from requirement priority, task order, file names, perceived importance, implementation complexity, or common product practice.

If the selected target or its membership is not explicit enough to determine consequential inclusion/exclusion, the review returns `BLOCKED_DECISION` / `CLARIFICATION_REQUIRED` rather than guessing.

### Item target disposition

Every discovered requirement, acceptance criterion, success criterion, mandatory gate and consequential checklist/review obligation receives exactly one target disposition:

- `REQUIRED_NOW`
- `EXPLICITLY_DEFERRED`
- `NOT_APPLICABLE_WITH_REASON`

`EXPLICITLY_DEFERRED` MUST identify the authoritative deferral source and, where known, destination phase/MVP/future SPEC. It never means satisfied.

`NOT_APPLICABLE_WITH_REASON` requires evidence that the item genuinely does not apply to the selected target/context; lack of implementation is not evidence of non-applicability.

### Evaluation status

Every `REQUIRED_NOW` item receives exactly one evaluation status:

- `SATISFIED`
- `UNSATISFIED`
- `NOT_VERIFIED`
- `BLOCKED`

A global approval is impossible while any `REQUIRED_NOW` item is `UNSATISFIED`, `NOT_VERIFIED` or `BLOCKED`.

### Review output classification

Review observations MUST be separated into:

- `DEFECT_AGAINST_TARGET`: concrete failure against a `REQUIRED_NOW` contract.
- `REGRESSION_AGAINST_PRESERVED_BEHAVIOR`: behavior required to remain unchanged but demonstrably changed.
- `MISSING_ACCEPTANCE_EVIDENCE`: implementation may be correct, but required proof was not executed or is unavailable.
- `SCOPE_EXPANSION_PROPOSAL`: useful capability or behavior not required by the selected target.
- `FUTURE_HARDENING_PROPOSAL`: robustness/operability improvement beyond the selected target.

A proposal MUST NOT be promoted to a blocking defect unless an authoritative requirement makes it `REQUIRED_NOW`.

Conversely, a missing requirement MUST NOT be downgraded to a proposal merely because the reviewer believes a smaller MVP would be reasonable.

## Architectural Decisions

### AD-001 — Delivery target is explicit review input/state

`implement-review` MUST resolve the delivery target before producing a consequential verdict.

Target authority order is:

```text
constitution / mandatory project policy
> explicit user/product decision
> active SPEC explicit target/phase/MVP declarations
> plan/contracts/tasks explicit allocation
> reviewer interpretation (non-authoritative)
```

Reviewer interpretation may discover ambiguity; it cannot resolve ambiguity by itself.

### AD-002 — Requirement inventory is complete before approval

The reviewer MUST build a machine-readable inventory from all authoritative active-SPEC surfaces that can impose acceptance obligations, including at least when present:

```text
spec.md functional requirements
user-story acceptance scenarios
success criteria
plan decisions / phase allocation
contracts
checklists designated as mandatory
constitution / mandatory project policy
explicit user decisions attached to the review context
```

The review MUST prove coverage of every discovered consequential item. Sampling is insufficient for final approval.

### AD-003 — No silent scope assumptions

The following are forbidden as scope evidence by themselves:

- P1/P2/P3 priority;
- task ordering;
- unchecked/checked state alone;
- an issue/PR title saying "MVP" without defining membership;
- absence of implementation;
- reviewer judgment that a feature is "probably future work";
- reviewer judgment that a feature "should be included" for completeness;
- passing unit tests unrelated to the requirement;
- generic industry practice.

Ambiguous scope blocks or requests clarification.

### AD-004 — Approval is target-qualified

A review verdict MUST identify the exact target it approves.

Examples:

```text
APPROVED target=MVP_MIN
APPROVED target=CURRENT_PHASE phase=Phase-2
APPROVED target=FULL_SPEC
```

`APPROVED target=MVP_MIN` MUST NOT be represented as proof that the whole SPEC is complete.

If a workflow requires full-SPEC completion, only `FULL_SPEC` approval satisfies that workflow gate.

### AD-005 — Same-SPEC implementation evidence is causally scoped

The predecessor gate MUST NOT accept the conjunction:

```text
active SPEC tasks complete
AND
some non-documentation branch/worktree delta exists
```

as sufficient same-SPEC proof.

Repository evidence MUST be bound to the active SPEC through a deterministic baseline/manifest/fingerprint or another equally strong mechanism.

At minimum, evidence MUST contain or derive:

```text
active SPEC identity
intent/spec fingerprint
implementation baseline identity
implementation result snapshot/HEAD or bounded delta
non-documentation changed paths attributable to that bounded implementation interval
```

A code delta belonging only to SPEC-A MUST NOT satisfy the predecessor gate for SPEC-B.

### AD-006 — Do not restore the removed implementation wrapper

The stronger predecessor proof MUST remain compatible with upstream `speckit-implement` and MUST NOT require restoring the removed PowerPack `speckit.implement` command.

A PowerPack-owned pre/post hook, phase manifest, baseline state or other generic infrastructure MAY record the evidence boundary as long as it does not become a hidden replacement implementation command.

### AD-007 — Intent changes invalidate implementation evidence

If authoritative active-SPEC intent changes after the recorded implementation baseline/result, the evidence is stale unless the system can deterministically prove the implementation covers the new intent.

The safe default is:

```text
intent fingerprint changed
  -> implementation evidence STALE
  -> re-run appropriate implementation/convergence path
```

### AD-008 — Verification gaps are not silently converted into pass/fail

Required acceptance execution that has not happened is `MISSING_ACCEPTANCE_EVIDENCE`, not `SATISFIED` and not automatically `DEFECT_AGAINST_TARGET`.

Examples include:

- required live end-to-end review flow not executed;
- required Windows installer/homologation not executed;
- CI workflow associated with the reviewed HEAD is `skipped` rather than successful;
- external integration prerequisite prevents the required smoke test.

If that evidence is mandatory for the selected target, the final status is `NOT_VERIFIED`/blocked from approval until the evidence exists or an explicit authoritative scope decision changes the target.

### AD-009 — CI state is interpreted literally

`success` may satisfy a configured CI requirement.

`skipped`, `cancelled`, `neutral`, `timed_out`, absent, stale-SHA or unrelated workflow state MUST NOT be reported as a successful CI validation without an explicit policy saying that state is acceptable.

### AD-010 — Reviews distinguish current defects from new capacity

Every proposed change raised during PR review MUST identify why it belongs in the current target.

If no current requirement supports it, it is recorded as `SCOPE_EXPANSION_PROPOSAL` or `FUTURE_HARDENING_PROPOSAL` and MUST NOT block approval of an otherwise complete target.

This protects the project's explicit distinction between a real defect and a new capability request.

### AD-011 — Full SPEC, phases and MVPs are all first-class but non-interchangeable

The review engine MUST support all four target modes without bias toward one:

```text
FULL_SPEC
CURRENT_PHASE
MVP_MIN
MVP_MAX
```

No mode is a fallback for missing scope information.

A project may intentionally deliver a phase or MVP while the full SPEC remains open, but that state must be explicit in the output.

### AD-012 — Cross-session review state is durable and snapshot-bound

The resolved delivery target, requirement inventory, dispositions and evidence snapshot SHOULD be persisted in project-local PowerPack JSON so later sessions can continue deterministically.

Persisted state MUST include sufficient fingerprints to become `STALE` when authoritative target membership, requirements, implementation snapshot or reviewed PR head changes.

ENV MUST NOT be the durable source of target or acceptance state.

### AD-013 — Findings-to-repair loops re-evaluate the matrix

After implementation changes made to resolve findings:

```text
implementation changes
  -> invalidate prior implementation/review snapshot
  -> convergence
  -> quality gate
  -> rebuild/revalidate target matrix as needed
  -> fresh semantic review
  -> fresh Project+GitHub review
```

A previously satisfied item is not blindly reused if its evidence depended on the old snapshot.

### AD-014 — Review completion has two explicit dimensions

The output MUST distinguish:

```text
target_completion
full_spec_completion
```

For example:

```json
{
  "target": "MVP_MIN",
  "target_completion": "APPROVED",
  "full_spec_completion": "INCOMPLETE_BY_EXPLICIT_SCOPE"
}
```

This prevents an MVP approval from being mistaken for completion of the entire specification.

## User Scenarios & Testing

### User Story 1 — Review the complete SPEC without omissions (Priority: P1)

A maintainer selects `FULL_SPEC`. Every applicable requirement and acceptance obligation is inventoried and individually evaluated.

**Acceptance Scenarios**:

1. Every discovered consequential item has a target disposition.
2. Every `REQUIRED_NOW` item has an evaluation status and evidence.
3. One unverified or unsatisfied required item prevents full-SPEC approval.
4. The review reports coverage counts that reconcile exactly with the inventory.

### User Story 2 — Review only an explicitly defined current phase (Priority: P1)

A SPEC is intentionally implemented in phases and the current PR targets one named phase.

**Acceptance Scenarios**:

1. Only items explicitly allocated to the current phase are `REQUIRED_NOW`.
2. Items assigned to later phases remain visible as `EXPLICITLY_DEFERRED`, not `SATISFIED`.
3. A missing allocation that materially changes the verdict yields clarification/blocking rather than inference.
4. Approval is labelled with the phase and does not assert full-SPEC completion.

### User Story 3 — Review minimum and maximum MVP boundaries explicitly (Priority: P1)

A project defines minimum and maximum MVP acceptance sets.

**Acceptance Scenarios**:

1. `MVP_MIN` approval proves exactly the minimum set and nothing more.
2. `MVP_MAX` includes every explicitly defined maximum-MVP item.
3. Priority labels alone never determine MVP membership.
4. An undefined MVP boundary blocks target resolution rather than creating a reviewer-defined MVP.

### User Story 4 — Reject cross-SPEC implementation evidence (Priority: P1)

Two SPECs have completed tasks, but the branch contains implementation delta only for one of them.

**Acceptance Scenarios**:

1. SPEC-A implementation evidence cannot satisfy SPEC-B.
2. Completed `tasks.md` plus unrelated code changes returns a deterministic evidence mismatch/no-delta-for-active-SPEC outcome.
3. Evidence becomes stale when the active SPEC intent fingerprint changes.
4. The solution does not require the removed PowerPack implementation wrapper.

### User Story 5 — Report missing homologation as evidence gap (Priority: P1)

A required live E2E or platform acceptance test has not run.

**Acceptance Scenarios**:

1. The review emits `MISSING_ACCEPTANCE_EVIDENCE` with the exact missing execution.
2. It does not claim success based only on static/unit coverage when the target requires live acceptance.
3. It does not claim a product defect unless actual execution demonstrates one.
4. Required missing evidence prevents approval of the selected target.

### User Story 6 — Treat skipped CI literally (Priority: P1)

The PR HEAD has a CI workflow whose conclusion is `skipped`.

**Acceptance Scenarios**:

1. `skipped` is not shown as a passing CI run.
2. Policy determines whether CI is required for the selected target.
3. If required, the matrix marks the CI obligation `NOT_VERIFIED` or `BLOCKED`.

### User Story 7 — Separate defect from improvement proposal (Priority: P1)

A reviewer notices a useful enhancement not required by the selected target.

**Acceptance Scenarios**:

1. The enhancement is classified as a proposal rather than a blocking defect.
2. The output states the absence of a current authoritative requirement.
3. If a current requirement is later identified, the observation may be reclassified with evidence.
4. A real missing requirement is never downgraded merely to make the target pass.

### User Story 8 — Resume deterministically in another session (Priority: P2)

A later agent/session resumes the same review.

**Acceptance Scenarios**:

1. It reloads target/matrix state from durable project-local data.
2. It validates SPEC, target, intent and PR/snapshot fingerprints before reuse.
3. Changed authoritative artifacts make the prior matrix stale.
4. It never depends on an ENV variable surviving from the previous session.

## Conceptual Review Target State

```json
{
  "schema_version": 1,
  "state_type": "implement-review-target",
  "spec": "specs/004-implement-review-adjustments",
  "target": {
    "mode": "CURRENT_PHASE",
    "name": "Phase-2",
    "authority": "spec.md#Delivery-Phases",
    "fingerprint": "sha256:..."
  },
  "implementation_evidence": {
    "spec_fingerprint": "sha256:...",
    "baseline": "<commit-or-manifest-id>",
    "result_head": "<sha>",
    "changed_paths_digest": "sha256:...",
    "validity": "FRESH"
  },
  "items": [
    {
      "id": "FR-007",
      "source": "spec.md",
      "target_disposition": "REQUIRED_NOW",
      "evaluation": "SATISFIED",
      "evidence": ["tests/...", "review finding evidence..."]
    },
    {
      "id": "FR-020",
      "source": "spec.md",
      "target_disposition": "EXPLICITLY_DEFERRED",
      "authority": "plan.md#Phase-3"
    }
  ],
  "target_completion": "APPROVED",
  "full_spec_completion": "INCOMPLETE_BY_EXPLICIT_SCOPE",
  "reviewed_head": "<sha>",
  "updated_at": "<timestamp>"
}
```

## Functional Requirements

- **FR-001**: `implement-review` MUST resolve exactly one active SPEC before predecessor validation or review.
- **FR-002**: A consequential review verdict MUST resolve exactly one explicit delivery target: `FULL_SPEC`, `CURRENT_PHASE`, `MVP_MIN` or `MVP_MAX`.
- **FR-003**: Target membership MUST come from authoritative artifacts or explicit user/product decisions; the reviewer MUST NOT infer membership from priority/order/absence/common practice.
- **FR-004**: Ambiguous consequential target membership MUST yield clarification/blocking state rather than an assumption.
- **FR-005**: The reviewer MUST build a complete inventory of applicable requirements, acceptance scenarios, success criteria and mandatory gates for the active SPEC/target.
- **FR-006**: Every inventoried item MUST receive exactly one target disposition: `REQUIRED_NOW`, `EXPLICITLY_DEFERRED` or `NOT_APPLICABLE_WITH_REASON`.
- **FR-007**: Every `REQUIRED_NOW` item MUST receive exactly one evaluation status with concrete evidence.
- **FR-008**: Global target approval MUST fail while any `REQUIRED_NOW` item is `UNSATISFIED`, `NOT_VERIFIED` or `BLOCKED`.
- **FR-009**: `EXPLICITLY_DEFERRED` MUST cite its authoritative deferral and MUST NOT count as satisfaction/full-SPEC completion.
- **FR-010**: `NOT_APPLICABLE_WITH_REASON` MUST contain a concrete applicability rationale/evidence.
- **FR-011**: Approval output MUST be qualified with the exact selected target and MUST separately report full-SPEC completion state.
- **FR-012**: The implementation predecessor gate MUST bind repository evidence to the active SPEC; unrelated branch/worktree changes MUST NOT satisfy it.
- **FR-013**: Same-SPEC evidence MUST include or deterministically derive active SPEC identity/fingerprint, implementation baseline and bounded implementation result/delta.
- **FR-014**: Intent changes that invalidate the implementation evidence boundary MUST mark the evidence stale.
- **FR-015**: The evidence mechanism MUST remain compatible with upstream `speckit-implement` and MUST NOT restore the removed PowerPack implementation wrapper.
- **FR-016**: Required but unexecuted acceptance/homologation MUST be classified as `MISSING_ACCEPTANCE_EVIDENCE` / `NOT_VERIFIED`, not silently treated as pass.
- **FR-017**: A failing executed acceptance test MAY create a defect; absence of execution alone MUST NOT be misreported as an observed implementation defect.
- **FR-018**: CI conclusions MUST be interpreted literally; `skipped` MUST NOT be represented as `success` without explicit policy authority.
- **FR-019**: Review observations MUST distinguish target defects/regressions, missing evidence, scope expansion proposals and future hardening proposals.
- **FR-020**: A proposal with no authoritative current-target requirement MUST NOT block target approval.
- **FR-021**: A real current-target gap MUST NOT be downgraded to proposal/debt merely to obtain approval.
- **FR-022**: Findings repaired by implementation changes MUST invalidate snapshot-bound approvals and trigger fresh target-matrix/evidence validation.
- **FR-023**: Cross-session target/matrix state, if persisted, MUST be project-local, fingerprinted and reloadable without ENV dependence.
- **FR-024**: Machine-readable review output MUST expose inventory counts by disposition/evaluation and allow exact reconciliation to the discovered item set.
- **FR-025**: Final full-SPEC completion MUST require `FULL_SPEC` target coverage or an equivalent explicit authoritative declaration that all SPEC obligations are complete.

## Success Criteria

- **SC-001**: A cross-SPEC fixture where SPEC-B has completed tasks but only SPEC-A has a code delta is rejected for SPEC-B in 100% of contract tests.
- **SC-002**: Target inventory counts reconcile exactly: discovered items = required-now + explicitly-deferred + not-applicable-with-reason.
- **SC-003**: Every required-now item has exactly one evaluation status and evidence record.
- **SC-004**: No ambiguous phase/MVP fixture is approved through reviewer inference; each returns deterministic clarification/blocking state.
- **SC-005**: `MVP_MIN`, `MVP_MAX`, `CURRENT_PHASE` and `FULL_SPEC` fixtures produce distinct, target-qualified completion results.
- **SC-006**: Approving an MVP/phase never sets full-SPEC completion to complete unless independent authoritative evidence establishes full completion.
- **SC-007**: Required unexecuted E2E/platform tests produce missing-evidence status in 100% of contract tests.
- **SC-008**: `skipped` CI fixtures are never reported as successful CI validation.
- **SC-009**: Review-proposal fixtures with no current-target requirement do not block approval; true current-target defects do.
- **SC-010**: Any implementation change after approval invalidates old snapshot-bound approval before a new final verdict can be issued.

## Assumptions

- Active Spec Kit artifacts remain the primary source of feature intent.
- Projects may use phased or MVP delivery, but the boundaries must be explicit before they can influence acceptance.
- It is acceptable for a selected phase/MVP to pass while the full SPEC remains incomplete, provided the output states that fact explicitly.
- Repository/git evidence can be bounded strongly enough to associate implementation changes with one active-SPEC implementation interval without reintroducing the removed wrapper command.
- Existing immutable PR/snapshot review semantics remain in force.

## Non-Goals

- Defining the product content of a project's MVP on the user's behalf.
- Guessing which requirements belong to a phase from priority or task order.
- Restoring `speckit.implement` or `speckit.converge` PowerPack wrappers.
- Treating every review improvement idea as a current defect.
- Allowing required work to be hidden as future improvement merely to produce approval.
- Treating static/unit coverage as automatically equivalent to a mandatory live acceptance test.
- Declaring full-SPEC completion from a phase/MVP-qualified approval.
