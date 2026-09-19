# SPEC-004 Contract — Rigorous PR Review Gates

This contract is a **normative companion** to `spec.md` for SPEC-004. Implementations and reviews of SPEC-004 MUST satisfy both documents. Where this contract is more specific about review-gate behavior, this contract controls that behavior.

## Purpose

`implement-review` is not a severity-threshold review. It is a convergence gate whose terminal approval requires the selected delivery target to have **zero unresolved findings** and complete required evidence.

The gate MUST preserve the explicit delivery-target model from SPEC-004:

```text
FULL_SPEC | CURRENT_PHASE | MVP_MIN | MVP_MAX
```

No reviewer, agent, hook or runtime may infer target membership merely to make the PR pass or fail.

## Rigorous gate sequence

A review round MUST execute in this order:

```text
resolve active SPEC
  -> resolve explicit delivery target
  -> build/revalidate complete target matrix
  -> prove same-SPEC implementation evidence
  -> run convergence
  -> run capability quality gate
  -> run independent semantic review
  -> run Project + GitHub deep PR review
  -> normalize every observation
  -> persist accepted findings into workflow artifacts
  -> submit formal GitHub review when findings exist
  -> repair all accepted findings
  -> rerun the complete affected gate sequence
  -> approve only with zero unresolved findings
```

A later gate MUST NOT erase or downgrade an unresolved obligation emitted by an earlier gate.

## Formal GitHub review outcome

When a review round produces one or more accepted findings against the selected target, the PR review outcome MUST be formalized as:

```text
REQUEST_CHANGES
```

A generic comment, summary, severity label, local JSON artifact or chat response is not a substitute for the formal review state when the integration is authorized to submit PR reviews.

`APPROVE` is allowed only after a fresh review of the current immutable PR snapshot proves all required gates clean.

If the integration cannot submit the formal GitHub review, the workflow MUST report `BLOCKED_CONFIGURATION` or equivalent explicit inability. It MUST NOT represent the PR as approved.

## Findings have no severity escape hatch

Severity may be retained as diagnostic metadata, but it MUST NOT determine whether an accepted finding is mandatory work.

For any observation accepted as a finding against the current target:

```text
BLOCKER | CRITICAL | HIGH | MEDIUM | LOW | INFO
                         -> mandatory resolution
```

Therefore:

- no severity is automatically ignorable;
- `LOW`, `INFO`, `minor`, `nit`, `suggestion` or similar wording does not permit an unresolved finding at approval time;
- a finding cannot be reclassified only to bypass the zero-finding gate;
- if an observation is genuinely outside the current target, it MUST be represented as a separate non-finding proposal backed by explicit target evidence, not as an unresolved finding.

## No technical-debt disposition for review findings

An accepted review finding MUST NOT be converted into, closed by, or considered resolved through:

- technical debt;
- backlog entry;
- TODO/FIXME;
- future hardening note;
- follow-up issue;
- future SPEC placeholder;
- deferred implementation without explicit target authority;
- reviewer suggestion to "address later".

A current-target finding remains current-flow work until implemented and revalidated.

If the observation is not required by the selected target, the reviewer must prove that fact from authoritative target membership and classify it as a non-blocking proposal. The workflow MUST NOT use "technical debt" as the mechanism that changes a finding into a proposal.

## Finding-to-artifact materialization

Every accepted finding MUST become traceable workflow work before the repair loop proceeds.

At minimum, the system MUST record:

```text
stable finding id
review round / reviewed snapshot
selected delivery target
source gate/reviewer
affected requirement or acceptance item
finding description
required repair
verification evidence required to close it
artifact links / paths
resolution status
```

### tasks.md

Every finding that requires implementation, test, configuration, documentation or executable verification work MUST be represented in the active SPEC `tasks.md` as explicit actionable work.

A finding MUST NOT be considered resolved merely because code changed; its corresponding task must be completed and the finding must be re-evaluated on the fresh snapshot.

### checklists

When a finding exposes a requirements-quality, acceptance-coverage, ambiguity, consistency, compliance or repeated-review gap that should remain testable, the applicable checklist artifact MUST be created or updated.

Checklist updates MUST follow the checklist-converge authority rules: they test requirements quality and MUST NOT invent product intent.

### spec / plan / contracts

When a finding proves that an authoritative requirement, phase boundary, MVP membership, contract or acceptance rule is missing or ambiguous, the responsible authoritative artifact MUST be corrected through the proper clarification/decision flow before implementation is treated as complete.

The review agent MUST NOT silently invent the missing requirement.

## Zero-finding invariant

Terminal approval for the selected target requires all of the following simultaneously:

```text
unresolved_target_findings == 0
unmaterialized_accepted_findings == 0
required_tasks_incomplete == 0
required_checklist_obligations_unresolved == 0
required_acceptance_evidence_missing == 0
blocking_decisions == 0
quality_gate == PASS | explicitly valid NOT_APPLICABLE
semantic_review == APPROVED
project_github_review == APPROVED
all approvals reference same current snapshot
```

No numeric severity threshold may replace this invariant.

## Proposal boundary

A reviewer may discover useful work outside the selected delivery target. Such an observation is not a finding only when there is positive evidence that it is outside the selected target.

Allowed non-finding classifications are:

```text
SCOPE_EXPANSION_PROPOSAL
FUTURE_HARDENING_PROPOSAL
```

These proposals:

- MUST be clearly separated from findings;
- MUST cite why they are outside the current target;
- MUST NOT be suggested as technical debt required to close the PR;
- MUST NOT be silently inserted into current `tasks.md` unless the user/product owner explicitly expands the target;
- MUST NOT block current-target approval.

If target membership is ambiguous, the correct result is clarification/blocking, not a proposal assumption.

## Repair loop

For every accepted finding:

```text
finding
  -> materialize task/checklist/spec-contract work as applicable
  -> implement all required work
  -> mark task complete only with evidence
  -> converge
  -> quality gate
  -> fresh semantic review
  -> fresh Project + GitHub review
```

Any implementation or authoritative-artifact change invalidates prior snapshot-bound approval.

## Deterministic acceptance examples

### Finding labeled LOW

```text
observation is REQUIRED_NOW defect
severity=LOW
=> REQUEST_CHANGES
=> task required
=> repair required
=> fresh review required
```

### Reviewer calls it a suggestion, but SPEC requires it

```text
observation maps to REQUIRED_NOW FR/SC/acceptance
reviewer wording="suggestion"
=> normalize to finding
=> REQUEST_CHANGES
=> mandatory repair
```

### Useful idea outside MVP_MIN

```text
positive authoritative evidence: item belongs to later phase
=> FUTURE_HARDENING_PROPOSAL or SCOPE_EXPANSION_PROPOSAL
=> not a finding
=> does not block MVP_MIN
=> no technical-debt workaround required
```

### Missing scope authority

```text
reviewer suspects item may be future work
no authoritative phase/MVP membership exists
=> CLARIFICATION_REQUIRED / BLOCKED_DECISION
=> do not infer deferment
```

## Required contract tests

The implementation MUST include tests proving at least:

1. one unresolved `LOW` finding prevents approval;
2. one unresolved `INFO`/`suggestion` that maps to `REQUIRED_NOW` prevents approval;
3. findings cannot be closed with `technical_debt`, `backlog`, `todo` or equivalent dispositions;
4. an accepted implementation finding creates/requires a `tasks.md` work item;
5. a requirements-quality finding creates/requires checklist/authoritative-artifact work when applicable;
6. GitHub review is `REQUEST_CHANGES` whenever accepted findings remain and the integration can submit reviews;
7. a fresh `APPROVE` is possible only when the current snapshot has zero unresolved findings and all mandatory gates are clean;
8. an explicitly out-of-target proposal remains non-blocking without being mislabeled as debt;
9. an ambiguous proposal-vs-finding boundary blocks for clarification rather than guessing;
10. repaired findings are re-evaluated against the fresh immutable snapshot rather than closed from stale evidence.
