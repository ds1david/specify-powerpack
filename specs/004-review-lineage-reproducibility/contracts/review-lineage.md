# Implement-Review Lineage Contract

This contract defines the minimum machine semantics for SPEC-001A.

## Stable identities

```text
review_id = repository + pull_request_number + spec_id + workflow
```

`review_id` is stable across implementation changes.

```text
snapshot_id = immutable PR/spec/review-contract identity
```

At minimum, snapshot/review-contract evidence records:

- repository;
- pull request number;
- base ref/base SHA;
- merge-base;
- head SHA;
- complete changed-file set;
- active SPEC id and bundle digest;
- master prompt version/digest;
- review protocol version/digest.

## Hierarchy

```text
Review
  -> Round
      -> Attempt
          -> Conversation Segment
```

- **Round**: semantic review of one implementation snapshot.
- **Attempt**: repeated reviewer execution against the same snapshot/review contract.
- **Conversation Segment**: physical ChatGPT Project conversation used by an attempt.

Changing only the conversation segment MUST NOT change the round.

## Finding state

Allowed states:

```text
NEW
NEWLY_DISCOVERED
STILL_OPEN
PARTIALLY_RESOLVED
RESOLVED
INVALIDATED
REGRESSED
```

### Same-snapshot rule

For a previously open finding when the implementation snapshot is unchanged:

```text
allowed:
  STILL_OPEN
  INVALIDATED (evidence required against the finding itself)

forbidden:
  PARTIALLY_RESOLVED
  RESOLVED
```

### Changed-snapshot resolution

`RESOLVED` requires all of:

1. changed implementation snapshot;
2. relevant repair delta identified;
3. current implementation evidence;
4. verification against the original failure scenario.

An unrelated delta is insufficient.

### Invalidation

`INVALIDATED` means the earlier finding itself was wrong, duplicate, non-normative or assumption-invalid.

It is not a synonym for code repair.

### Regression

A finding that was validly resolved and later materially reappears is `REGRESSED`.

## Finding identity

PowerPack assigns an immutable finding id. Matching across attempts/rounds MUST NOT depend primarily on title text or source line number.

Matching SHOULD use stable anchors where available:

```text
authority_ref
category
repository-relative path
logical symbol/component
normalized failure-mode signature
```

A fingerprint is a matching aid; it does not replace the persisted finding id.

## Attempt reconciliation

Every valid same-snapshot attempt is immutable evidence.

A later attempt does not overwrite an earlier attempt.

Material disagreement about blocker existence, prior-finding state or verdict requires explicit reconciliation. If deterministic reconciliation cannot establish one valid state:

```text
BLOCKED_REVIEW_DIVERGENCE
```

Approval is forbidden while material divergence remains unresolved.

## Continuation

A continuation packet MUST contain enough authoritative information to resume without relying on Project memory:

```text
review_id
round
attempt
segment
snapshot identity
review-contract identity
checkpoint
open findings
prior finding states
required output schema
```

Conversation rollover is a transport event, not a workflow-state transition.

## Approval

`APPROVED` requires at minimum:

```text
same final immutable snapshot across required gates
zero unresolved findings
all prior findings accounted for
zero unresolved review divergence
complete required changed-file/requirement evidence
successful adversarial verdict challenge
zero blocking context gaps
```
