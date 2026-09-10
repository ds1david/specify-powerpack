# Requirements Checklist: Rigorous Implement Review

## Delivery target and scope

- [ ] CHK001 Exactly one review target is explicit: `FULL_SPEC`, `CURRENT_PHASE`, `MVP_MIN`, or `MVP_MAX`.
- [ ] CHK002 Target membership comes from authoritative artifacts or explicit user/product decisions, never reviewer assumption.
- [ ] CHK003 Every consequential obligation is inventoried and has one explicit target disposition.
- [ ] CHK004 Ambiguous phase/MVP membership blocks or requests clarification instead of being inferred.
- [ ] CHK005 Approval output distinguishes target completion from full-SPEC completion.

## Same-SPEC evidence

- [ ] CHK006 Implementation evidence is deterministically bound to the active SPEC.
- [ ] CHK007 Completed tasks plus unrelated branch/worktree code changes cannot satisfy the predecessor gate.
- [ ] CHK008 Active-SPEC intent changes invalidate stale implementation evidence when coverage cannot be proven.
- [ ] CHK009 The stronger evidence path does not restore the removed PowerPack `speckit.implement` wrapper.

## Findings are mandatory work

- [ ] CHK010 Every accepted current-target finding remains mandatory regardless of severity.
- [ ] CHK011 `LOW`, `INFO`, `minor`, `nit`, `suggestion`, or equivalent wording cannot bypass a current-target finding.
- [ ] CHK012 No accepted finding is resolved by converting it to technical debt, backlog, TODO/FIXME, future issue, or future SPEC.
- [ ] CHK013 Every finding requiring implementation/test/configuration/documentation/executable verification is materialized in active-SPEC `tasks.md`.
- [ ] CHK014 Applicable requirements-quality/coverage/ambiguity/consistency/compliance findings create or update checklist/authoritative artifacts.
- [ ] CHK015 Missing authoritative intent is clarified through the proper authority flow and is not invented by the reviewer.
- [ ] CHK016 Every finding remains traceable through artifact work, implementation/evidence, and fresh-review closure.

## Formal PR review

- [ ] CHK017 Any review round with accepted findings produces formal `REQUEST_CHANGES` when GitHub review submission is available.
- [ ] CHK018 A generic PR comment, chat summary, severity label, or local JSON artifact is not treated as equivalent to `REQUEST_CHANGES` when formal review is available.
- [ ] CHK019 Inability to submit a required formal review blocks explicitly rather than yielding approval.
- [ ] CHK020 Formal `APPROVE` is emitted only from a fresh review of the current immutable snapshot.

## Zero-finding terminal invariant

- [ ] CHK021 Terminal approval requires zero unresolved current-target findings.
- [ ] CHK022 Terminal approval requires zero accepted findings not yet materialized in workflow artifacts.
- [ ] CHK023 Terminal approval requires all review-generated required tasks completed with closure evidence.
- [ ] CHK024 Terminal approval requires all required checklist obligations resolved.
- [ ] CHK025 Terminal approval requires no mandatory acceptance evidence missing and no blocking decisions.
- [ ] CHK026 Quality, semantic-review, and Project+GitHub-review gates are clean for the same current snapshot.
- [ ] CHK027 Any implementation or authoritative-artifact change invalidates stale approvals and triggers fresh affected gates.

## Proposal boundary

- [ ] CHK028 A non-blocking proposal has positive evidence that it is outside the selected current target.
- [ ] CHK029 Out-of-target proposals are separated from findings and are not mislabeled as technical debt.
- [ ] CHK030 Ambiguous proposal-vs-finding membership blocks/clarifies rather than being guessed.
- [ ] CHK031 A current-target requirement is never downgraded to proposal merely to achieve approval.

## Verification evidence

- [ ] CHK032 Required but unexecuted E2E/platform/homologation is reported as missing evidence, not pass.
- [ ] CHK033 `skipped`, stale, absent, or unrelated CI is not represented as successful validation without explicit policy authority.
- [ ] CHK034 Contract tests cover low/info findings, forbidden debt dispositions, task/checklist materialization, formal `REQUEST_CHANGES`, and zero-finding `APPROVE`.
- [ ] CHK035 Cross-SPEC negative fixtures prove unrelated implementation delta cannot satisfy the active SPEC.
