# Tasks: Deterministic Implement Review Acceptance

**Feature**: `004-implement-review-adjustments`

These tasks operationalize `spec.md` and `contracts/rigorous-review-gates.md`.

## Phase 1 — Review target and matrix

- [ ] T001 Define a machine-readable delivery-target model supporting `FULL_SPEC`, `CURRENT_PHASE`, `MVP_MIN`, and `MVP_MAX` with explicit authority/fingerprint.
- [ ] T002 Build complete active-SPEC obligation inventory across FRs, user-story acceptance scenarios, SCs, contracts, mandatory checklists, constitution/project policy, and explicit user decisions.
- [ ] T003 Require exactly one target disposition for every discovered consequential item: `REQUIRED_NOW`, `EXPLICITLY_DEFERRED`, or `NOT_APPLICABLE_WITH_REASON`.
- [ ] T004 Block/clarify when phase/MVP membership would otherwise require reviewer inference.
- [ ] T005 Persist target/matrix state in project-local fingerprinted JSON and invalidate it when target authority or active-SPEC intent changes.

## Phase 2 — Same-SPEC implementation evidence

- [ ] T006 Replace branch-global non-documentation delta proof with a deterministic active-SPEC implementation boundary/manifest/fingerprint.
- [ ] T007 Prove that code changes attributable only to SPEC-A cannot satisfy SPEC-B predecessor validation.
- [ ] T008 Preserve compatibility with upstream `speckit-implement`; do not restore the removed PowerPack implementation wrapper.
- [ ] T009 Mark implementation evidence stale after consequential active-SPEC intent changes.
- [ ] T010 Add negative contract fixtures for completed tasks plus unrelated code delta.

## Phase 3 — Rigorous finding normalization

- [ ] T011 Normalize every review observation against the selected target before deciding whether it is a finding or an out-of-target proposal.
- [ ] T012 Ensure diagnostic severity never makes an accepted current-target finding optional.
- [ ] T013 Ensure labels/wording such as `LOW`, `INFO`, `minor`, `nit`, or `suggestion` cannot bypass a finding that maps to `REQUIRED_NOW`.
- [ ] T014 Keep `SCOPE_EXPANSION_PROPOSAL` and `FUTURE_HARDENING_PROPOSAL` separate from findings and require positive evidence that they are outside the selected target.
- [ ] T015 Return clarification/blocking when proposal-vs-finding membership is ambiguous rather than guessing.

## Phase 4 — No technical-debt escape hatch

- [ ] T016 Reject technical-debt, backlog, TODO/FIXME, future issue, future SPEC, or equivalent disposition as resolution of an accepted current-target finding.
- [ ] T017 Ensure a current-target finding remains unresolved until implemented and revalidated on a fresh snapshot.
- [ ] T018 Ensure out-of-target proposals are not mislabeled as technical debt merely to close the PR.
- [ ] T019 Add regression tests for forbidden finding dispositions (`technical_debt`, `backlog`, `todo`, `later`, or equivalent aliases).

## Phase 5 — Finding-to-artifact materialization

- [ ] T020 Give every accepted finding a stable id, source review round/snapshot, target, affected requirement/acceptance item, required repair, closure evidence, and resolution status.
- [ ] T021 Materialize every finding requiring implementation/test/configuration/documentation/executable verification as an explicit active-SPEC `tasks.md` work item.
- [ ] T022 Require task completion plus fresh finding re-evaluation; code changes alone do not close a finding.
- [ ] T023 Create/update applicable checklist artifacts when a finding exposes requirements-quality, acceptance-coverage, ambiguity, consistency, compliance, or repeated-review gaps.
- [ ] T024 Route missing/ambiguous authoritative product intent back to the proper spec/plan/contracts/clarification flow; do not let the reviewer invent it.
- [ ] T025 Preserve traceability from review finding -> task/checklist/spec artifact -> implementation/evidence -> fresh review closure.

## Phase 6 — Formal GitHub review gate

- [ ] T026 When accepted findings remain and GitHub review submission is authorized, submit formal `REQUEST_CHANGES` for the reviewed PR snapshot.
- [ ] T027 Do not treat a generic comment/local artifact/chat summary as equivalent to formal `REQUEST_CHANGES` when formal review submission is available.
- [ ] T028 If formal review submission is required but unavailable, return explicit blocked/configuration state rather than approval.
- [ ] T029 Allow formal `APPROVE` only after a fresh review of the current immutable snapshot proves zero unresolved target findings and all mandatory gates clean.
- [ ] T030 Verify stale approvals cannot survive implementation or authoritative-artifact changes.

## Phase 7 — Zero-finding terminal invariant

- [ ] T031 Encode terminal approval invariant: unresolved target findings = 0.
- [ ] T032 Encode terminal approval invariant: unmaterialized accepted findings = 0.
- [ ] T033 Encode terminal approval invariant: required review-generated tasks incomplete = 0.
- [ ] T034 Encode terminal approval invariant: required checklist obligations unresolved = 0.
- [ ] T035 Encode terminal approval invariant: required acceptance evidence missing = 0 and blocking decisions = 0.
- [ ] T036 Require quality gate pass or explicitly valid `NOT_APPLICABLE`, clean semantic review, clean Project+GitHub review, and same-snapshot approvals.

## Phase 8 — Required contract tests

- [ ] T037 Test that one unresolved `LOW` finding prevents approval.
- [ ] T038 Test that one unresolved `INFO`/`suggestion` mapping to `REQUIRED_NOW` prevents approval.
- [ ] T039 Test that accepted findings cannot be closed through technical-debt/backlog/TODO dispositions.
- [ ] T040 Test that implementation findings create/require `tasks.md` work and cannot close before task completion plus re-review.
- [ ] T041 Test that applicable requirements-quality findings create/require checklist or authoritative-artifact work.
- [ ] T042 Test that any remaining accepted finding produces `REQUEST_CHANGES` when GitHub review submission is available.
- [ ] T043 Test that `APPROVE` is possible only with zero unresolved findings on the current snapshot.
- [ ] T044 Test that an explicitly out-of-target proposal remains non-blocking and is not represented as technical debt.
- [ ] T045 Test ambiguous target membership blocks/clarifies rather than becoming automatic deferral/proposal.
- [ ] T046 Test repaired findings are re-evaluated against a fresh immutable snapshot.
- [ ] T047 Test required live/platform/CI acceptance evidence remains `NOT_VERIFIED` until actually satisfied according to policy.

## Phase 9 — Homologation

- [ ] T048 Run full target-matrix review fixtures for all four delivery targets and reconcile inventory counts exactly.
- [ ] T049 Run cross-SPEC implementation-evidence negative fixture.
- [ ] T050 Run a PR review fixture with at least one low-severity current-target finding and verify formal `REQUEST_CHANGES` plus task materialization.
- [ ] T051 Repair that fixture and verify the next fresh current-snapshot review reaches zero findings before `APPROVE`.
- [ ] T052 Record evidence that no review finding was converted to debt/backlog/TODO to obtain terminal approval.
