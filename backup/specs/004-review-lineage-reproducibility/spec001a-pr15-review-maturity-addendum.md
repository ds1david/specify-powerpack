# SPEC-001A Addendum — PR15 Review Maturity and Evidence-First Merge Gate

**Status**: Draft normative amendment proposal

**Parent**: `SPEC-001A — Review Lineage, GPT Web Continuity and Reproducibility`

**Source**: lessons learned from repeated adversarial Code Review rounds of PR15

## Purpose

This addendum converts recurring review-process failures observed during PR15 into durable `implement-review` contracts. The objective is to reduce review roundtrips caused by missing context, incomplete evidence, premature blocking and inconsistent requirement traceability.

This addendum does not change the ownership boundary already established by SPEC-001A. It strengthens the evidence and merge-gate protocol owned by SPEC-001A.

## 1. Review Readiness Gate

An `implement-review` MUST NOT enter substantive implementation review until the immutable review context is complete.

The pre-review Evidence Package MUST identify, at minimum:

```text
repository
pull_request_number
base_ref
base_sha
merge_base
head_sha
changed_files
spec_id
spec_bundle_sha256
review_protocol_version
review_protocol_sha256
master_prompt_version
master_prompt_sha256
```

If any required identity element cannot be proven from authoritative repository evidence, the review MUST enter a blocked context state rather than begin partial substantive review.

## 2. Requirement Traceability Contract

Every normative requirement selected for the review MUST be traceable through the following chain:

```text
requirement
  -> implementation evidence
  -> validation/test evidence
  -> observed result
```

The review package SHOULD expose a machine-readable matrix with:

```yaml
requirement_id:
statement:
implementation:
  files: []
  symbols: []
validation:
  tests: []
  commands: []
status:
```

A requirement without sufficient implementation or validation evidence MUST be classified as a verification gap rather than inferred to be compliant.

## 3. Three-Phase Review Model

The review lifecycle MUST distinguish three logical phases:

### Phase A — Context Integrity

Prove repository, PR, snapshot, active SPEC, changed files and review-contract identity.

### Phase B — Implementation Correctness

Evaluate implementation behavior, architecture, invariants, failure modes, persistence, concurrency, recovery and test quality as applicable to the active SPEC.

### Phase C — SPEC Compliance Merge Gate

Reconcile every requirement, prior finding, blocker, evidence gap and verdict against the same final immutable snapshot.

A substantive verdict MUST NOT be emitted from an incomplete Phase A.

## 4. Finding Classification

Every material review observation MUST have one primary classification:

```text
BUG
SPEC_VIOLATION
VERIFICATION_GAP
ARCHITECTURE_RISK
ENHANCEMENT
FUTURE_CAPABILITY
```

Only `BUG`, `SPEC_VIOLATION` and blocking `VERIFICATION_GAP` findings MAY block the merge gate when their blocking criteria are satisfied.

`ENHANCEMENT` and `FUTURE_CAPABILITY` MUST NOT become blockers merely because they are desirable.

`ARCHITECTURE_RISK` MUST identify the violated current authority or invariant before becoming a blocker.

## 5. Evidence-First Blocking

A blocker MUST contain all of the following:

```text
authority_reference
changed_file_or_contract_anchor
implementation_evidence
causal_failure_scenario
actual_behavior
required_behavior
impact
required_correction
verifiable_acceptance_criteria
```

A reviewer MUST NOT emit a blocker based solely on intuition, generic best practice, future design preference, or an unverified interpretation of the SPEC.

## 6. Anti-Roundtrip Full-Pass Rule

Finding the first blocker MUST NOT terminate the substantive review.

After identifying a blocker, the reviewer MUST continue through all mandatory review fronts and consolidate independent findings before returning the result.

At minimum the reviewer MUST perform:

```text
full changed-file pass
full requirement/acceptance pass
blast-radius/invariant pass
non-happy-path pass
regression/behavior-preservation pass
adversarial verdict challenge
```

A later review round SHOULD therefore be caused primarily by implementation changes or newly available authoritative evidence, not by a reviewer stopping after the first defect.

## 7. Self-Validation Before Review

The implementation owner SHOULD provide a PR self-validation declaration before requesting substantive review:

```yaml
implementation_ready: true
spec_mapped: true
tests_added_or_verified: true
changed_files_known: true
evidence_complete: true
```

A failed self-validation MUST be surfaced as `NOT_READY_FOR_REVIEW` or an equivalent context state instead of being disguised as an implementation defect.

## 8. Immutable Changed-File Coverage

`coverage.changed_files` MUST contain the complete changed-file set for the immutable snapshot under review.

A reviewer MUST NOT infer that an unlisted file is unchanged when the authoritative PR evidence says otherwise.

A coverage mismatch is a context-integrity failure and MUST block the merge gate until reconciled.

## 9. Contract Test Requirements

The implementation MUST add or maintain deterministic tests for:

- incomplete Evidence Package rejection;
- changed-file coverage mismatch;
- requirement-to-evidence traceability gaps;
- finding classification validation;
- blocker authority validation;
- anti-roundtrip full-pass behavior;
- prior-finding completeness;
- same-snapshot monotonicity;
- changed-snapshot resolution evidence;
- same-snapshot divergence;
- continuation/recovery behavior.

## 10. Review Metrics

The PowerPack review lifecycle SHOULD expose, at minimum:

```text
review_round_count
review_attempt_count
context_block_count
evidence_missing_count
finding_reopen_count
finding_resolution_count
same_snapshot_divergence_count
```

These metrics are process-quality signals. They MUST NOT themselves determine approval.

## 11. Recurring Finding → SPEC Evolution

When a review repeatedly identifies the same process-level deficiency across independent PRs or review rounds, the deficiency MUST be evaluated as a possible specification/process gap.

The preferred evolution path is:

```text
recurring review failure
  -> process gap
  -> durable normative rule
  -> SPEC amendment
  -> future PR inheritance
```

The same deficiency MUST NOT be rediscovered indefinitely as an ad-hoc reviewer comment.

## 12. Scope-Control Rule

A review MUST distinguish:

```text
current contract violation
current verification failure
architecture risk against current authority
future capability
engineering preference
```

Only the first three categories can become blocking findings, and only with evidence satisfying the blocker contract.

This prevents Code Review from becoming an uncontrolled product-discovery or backlog-generation process.

## 13. Final Approval Preconditions

Before `APPROVED`, the merge gate MUST establish:

```text
context complete
changed-file coverage complete
requirements accounted for
prior findings accounted for
blocking findings resolved or otherwise validly closed
review divergence resolved
required validation evidence present
full review pass completed
adversarial verdict challenge completed
```

The verdict MUST bind to the exact immutable snapshot whose evidence was reviewed.

## 14. Recommended Evidence Manifest

The implementation SHOULD generate a review manifest similar to:

```json
{
  "schema_version": "1.0",
  "review_context": {
    "repository": "owner/repository",
    "pull_request_number": 15,
    "base_ref": "main",
    "base_sha": "<40-char-sha>",
    "merge_base": "<40-char-sha>",
    "head_sha": "<40-char-sha>",
    "snapshot_sha256": "<sha256>",
    "spec_id": "001-single-skill-baseline"
  },
  "coverage": {
    "changed_files": []
  },
  "requirements": [],
  "findings": []
}
```

The manifest is evidence metadata, not a replacement for authoritative GitHub evidence.

## 15. Invariants Added by This Addendum

```text
review_start
  => context_integrity_proven
```

```text
blocker
  => authority
  => evidence
  => causal_failure
  => acceptance_criteria
```

```text
first_blocker
  != review_end
```

```text
changed_files_manifest
  == immutable_pr_changed_files
```

```text
requirement
  => implementation_evidence
  => validation_evidence
```

```text
future_capability
  != current_spec_violation
```

```text
recurring_process_failure
  => candidate_SPEC_evolution
```
