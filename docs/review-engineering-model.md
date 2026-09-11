# PowerPack Review Engineering Model

## Purpose

This document defines the engineering workflow that should surround `implement-review` so that substantive review time is spent on correctness and architecture rather than reconstructing repository context.

The model is derived from repeated review rounds of PR15 and complements SPEC-001A.

## Lifecycle

```text
SPEC freeze
  -> implementation
  -> PR self-validation
  -> Evidence Package validation
  -> Context Integrity Review
  -> Implementation Correctness Review
  -> SPEC Compliance Merge Gate
```

A PR is not review-ready merely because it compiles or has tests. It is review-ready when the immutable context and evidence package are complete enough for another reviewer to reproduce the evaluation.

## Evidence Package

The package should contain:

- repository and PR identity;
- base ref/SHA;
- merge base;
- head SHA;
- complete changed-file list;
- active SPEC identity and digest;
- review protocol identity and digest;
- master prompt identity and digest;
- requirement-to-implementation mapping;
- requirement-to-validation mapping;
- prior finding inventory.

Missing identity is a context failure, not a code finding.

## Traceability

The minimum traceability chain is:

```text
SPEC requirement
   -> implementation location
   -> validation/test
   -> observed evidence
   -> reviewer conclusion
```

The reviewer should never have to reconstruct this mapping from scratch when the PR is ready for review.

## Review Phases

### Context Integrity Review

Validate the immutable snapshot and the completeness of the evidence package.

### Implementation Correctness Review

Perform the deep technical review defined by the active SPEC and the master review protocol.

### SPEC Compliance Merge Gate

Reconcile requirements, prior findings, current findings, divergence and final verdict against the same snapshot.

## Anti-Roundtrip Protocol

The first blocker is a finding, not an exit condition.

After a blocker is found, the reviewer continues through the mandatory review fronts and consolidates independent findings. This is the principal mechanism for reducing avoidable review rounds.

A new round should normally be justified by one of:

- implementation changed;
- authoritative SPEC/contract changed;
- previously unavailable authoritative evidence became available;
- a genuine review divergence requires reconciliation.

It should not be justified merely because the first reviewer stopped before completing the required review surface.

## Finding Taxonomy

Use one primary classification:

```text
BUG
SPEC_VIOLATION
VERIFICATION_GAP
ARCHITECTURE_RISK
ENHANCEMENT
FUTURE_CAPABILITY
```

This keeps desired improvements from silently becoming merge blockers.

## Definition of Ready for Review

A PR should satisfy:

```yaml
implementation_ready: true
spec_mapped: true
tests_added_or_verified: true
changed_files_known: true
evidence_complete: true
```

## Definition of Done for Merge Gate

The merge gate requires:

```text
context proven
+ changed-file coverage proven
+ all applicable requirements accounted for
+ prior findings accounted for
+ blockers resolved/invalidated with evidence
+ no unresolved material divergence
+ validation evidence complete
+ full review pass complete
+ adversarial verdict challenge complete
```

## Process Learning Loop

Recurring review failures are process signals:

```text
repeated finding
   -> identify process gap
   -> encode durable rule
   -> amend SPEC/process contract
   -> future PRs inherit the rule
```

This prevents the project from paying the same review cost repeatedly.
