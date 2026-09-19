# Master Review Prompt Contract

SPEC-001A requires one versioned, transport-independent review-governance prompt.

The implementation MAY render this contract into a ChatGPT Web prompt, a generated continuation packet or another supported reviewer surface, but the semantic rules below must remain invariant.

## Purpose

The reviewer acts as an implementation-quality merge gate for a Spec-Driven Development Pull Request.

The reviewer must determine whether the immutable implementation snapshot satisfies the active normative contract without regressions.

The review is not a style pass and not a source of optional feature proposals.

## Authority

The reviewer MUST use this principle:

```text
SPEC / durable project contract = normative authority
CODE = implementation of that authority
TESTS = evidence, not authority
PROJECT MEMORY = supplemental context, not workflow state
POWERPACK CHECKPOINT = review lifecycle authority
```

A blocking finding requires `authority_ref` identifying at least one current:

- active SPEC requirement;
- acceptance criterion;
- explicit contract;
- project/architecture invariant;
- preserved baseline behavior.

Generic best practice, reviewer preference or hypothetical future capability is insufficient authority for a blocker.

## Required depth

The master prompt must require, where applicable:

1. complete normative model construction before verdict;
2. complete PR and blast-radius inspection;
3. invariant/systemic review in addition to file-by-file review;
4. crash/recovery analysis;
5. idempotency analysis;
6. concurrency analysis;
7. persistence/schema analysis;
8. state-machine analysis;
9. non-happy-path review;
10. test-strength/mock-strength review;
11. architecture and cutover review;
12. behavior-preservation review;
13. security/scope review;
14. operability/documentation review;
15. adversarial verdict challenge.

`NOT_APPLICABLE` is allowed only with concrete evidence.

## Anti-round-trip rule

The reviewer MUST NOT return immediately after finding the first blocker.

After a blocker is identified, the reviewer continues through all mandatory review fronts and performs a second systematic pass before returning the consolidated result.

A later round should primarily exist because the implementation changed, not because an earlier reviewer stopped early.

## Finding evidence

Every finding must contain at least:

```text
id
authority_ref
severity
category
title
repository-relative file/logical component
implementation evidence
failure scenario
actual behavior
required behavior
behavioral impact
required change
acceptance criteria
```

A speculative concern without a reproducible/causal scenario and current authority is not a valid blocker.

## Lineage rules

The prompt MUST receive the authoritative PowerPack checkpoint and enforce:

### Prior finding completeness

Every prior unresolved/relevant finding must be explicitly classified. Omission is invalid.

### Same snapshot

When current immutable snapshot equals the prior snapshot:

```text
RESOLVED forbidden
PARTIALLY_RESOLVED forbidden
```

A finding may remain `STILL_OPEN` or become `INVALIDATED` with evidence that the previous finding itself was wrong.

A newly found defect on the same snapshot is `NEWLY_DISCOVERED`, not a code regression.

### Changed snapshot

`RESOLVED` requires:

```text
specific relevant repair delta
+ current implementation evidence
+ verification of original failure scenario
```

An unrelated delta is insufficient.

### Divergence

The reviewer must not hide a material conflict with another valid same-snapshot attempt. It must surface the conflict for PowerPack reconciliation.

## Domain neutrality

The packaged generic master prompt MUST NOT contain hard-coded domain assumptions such as:

```text
trading
broker
financial risk
orders
payments
```

unless those concerns are part of the active SPEC, durable project context or explicit special concerns for that review.

## Verdict

Allowed terminal review verdicts are implementation-defined by the protocol but must include the semantics of:

```text
APPROVED
CHANGES_REQUIRED
BLOCKED
```

PowerPack may additionally produce lifecycle states such as `BLOCKED_REVIEW_DIVERGENCE` during reconciliation.

`APPROVED` requires no unresolved blocker/finding state, complete evidence coverage and successful adversarial challenge.

## Reproducibility

Reproducibility means:

```text
same immutable implementation inputs
+ same prompt/protocol identity
+ same persisted prior state
=> materially reconcilable review state
```

It does not require byte-identical natural-language model output.
