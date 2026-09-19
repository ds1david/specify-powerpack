# Feature Specification: SPEC-001A — Review Lineage, GPT Web Continuity and Reproducibility

**Feature Branch**: `004-review-lineage-reproducibility`

**Created**: 2026-09-11

**Status**: Draft

**Normative Alias**: `SPEC-001A`

**Amends**: `SPEC-001 — Single Skill Baseline`

**Input**: User description: "Remodel the SPEC-001 implement-review implementation so the independent review is owned by a reproducible PowerPack review lifecycle, uses the bound ChatGPT Project/GPT Web review workspace with GitHub evidence, survives ChatGPT conversation limits through controlled rollover, preserves prior findings across rounds and repeated attempts, and prevents probabilistic reviewer variation from silently resolving, losing or inventing blocker state. Reconcile later specifications so SPEC-001 + SPEC-001A exclusively own implement-review semantics while later specs own plugin infrastructure or other capabilities."

## Overview

SPEC-001 established `implement-review` as the baseline PowerPack functional capability and preserved the ChatGPT Project + GitHub review path. This amendment keeps that product decision while replacing the review-continuity model with an explicit, persistent and reproducible review lifecycle.

The central rule is:

```text
logical review != ChatGPT conversation
```

A logical review is a PowerPack workflow entity. A ChatGPT Project conversation is a bounded execution segment of that review. Conversation exhaustion, rollover, branching, archiving or deletion MUST NOT advance, resolve or corrupt the review lifecycle.

The PowerPack owns:

```text
review identity
snapshot identity
round / attempt / segment lifecycle
review checkpoint
finding identity and lifecycle
review protocol / master prompt version
result validation and reconciliation
```

ChatGPT Web / the bound ChatGPT Project owns the interactive reviewer execution surface. GitHub evidence is obtained through the GitHub connector available to that Project. Project memory and historical conversations are useful supplementary context but are never the authoritative workflow ledger.

This amendment deliberately targets capabilities that are implementable with the product constraints available today. It MUST NOT require an unsupported public API for programmatically creating a ChatGPT Project conversation or appending a message to an existing conversation. The baseline workflow MAY require the user to create a new Project conversation, paste a generated continuation packet and import the structured result.

## Normative Relationship to SPEC-001

SPEC-001 remains authoritative for:

- the single-capability baseline established by SPEC-001;
- preservation of `implement-review`;
- removal of the legacy PowerPack capabilities covered by SPEC-001;
- same-SPEC implementation predecessor evidence;
- baseline installation/discovery/cleanup behavior;
- all SPEC-001 requirements not explicitly amended here.

SPEC-001A is the authoritative amendment for the independent implementation-review subsystem.

Where SPEC-001 prescribes transport- or continuity-specific behavior for the ChatGPT Project/GitHub review path, this specification supersedes those details only to the extent necessary to implement the lifecycle defined here.

SPEC-001A MUST NOT reopen or weaken unrelated SPEC-001 baseline requirements.

## Cross-Spec Responsibility Boundary

The following ownership model is normative:

```text
CAPABILITY OWNER
    owns what the capability means and how its state machine behaves

INFRASTRUCTURE OWNER
    owns generic registration/configuration/persistence/diagnostics mechanisms

ORCHESTRATOR
    owns when capabilities are invoked, not their internal semantics
```

For the current PowerPack roadmap:

| Authority | Exclusive responsibility |
|---|---|
| SPEC-001 | baseline product surface and initial preservation of `implement-review` |
| SPEC-001A (this SPEC) | complete `implement-review` review semantics and lifecycle |
| SPEC-002 | generic plugin infrastructure: bundle/extension/presets, setup, registry, generic config/state framework, component coherence, doctor/diagnostics |
| SPEC-003 | `checklist-converge` capability semantics |
| future orchestration specs | ordering between capabilities/stages, without redefining capability internals |

A later specification that intentionally changes capability-specific states, transitions, gates, provider behavior, finding semantics, approval semantics, evidence semantics or budgets MUST explicitly declare itself an amendment to that capability owner.

### Reconciliation with SPEC-002

SPEC-002 remains authoritative for generic infrastructure. Its environment discovery may report facts such as integration installation, executable availability, authentication readiness, connector readiness and component health.

SPEC-002 MUST NOT own the semantic decision of what those facts mean for `implement-review`.

For purposes of `implement-review`, the following SPEC-002 review-specific responsibilities are delegated to and superseded by SPEC-001A:

- review topology/evidence-backend semantics specific to `implement-review`;
- GPT Web / ChatGPT Project activation semantics specific to `implement-review`;
- review round accounting;
- prior-finding accounting;
- snapshot approval invalidation;
- review budget/exhaustion semantics;
- final review approval semantics.

In particular, SPEC-002 FR-021 through FR-024 and FR-032 through FR-036 MUST be interpreted as infrastructure hooks or historical draft intent, not as competing normative definitions of `implement-review`. The corresponding capability semantics are defined here.

SPEC-002 may still provide the registry, setup engine, generic persistent-state services, configuration storage and doctor surfaces consumed by this capability.

### Reconciliation with SPEC-003

SPEC-003 remains the exclusive owner of `checklist-converge` semantics: checklist classifications, participation policy, checklist/task hooks, clarification behavior, task staleness and checklist convergence budget.

Generic persistence mechanics duplicated in SPEC-003 (project-local JSON, revision checking, atomic replacement, cross-session reload and ENV non-authority) MUST converge on SPEC-002 generic infrastructure when that infrastructure exists. SPEC-003 retains ownership only of checklist-specific state fields and checklist-specific state transitions.

The `checklist-converge` convergence budget and the `implement-review` review budget are independent and MUST NOT share counters, exhaustion state or semantic meaning unless a future orchestration amendment explicitly coordinates them.

## Terminology

- **Review**: one logical `implement-review` lifecycle for one repository + PR + active SPEC.
- **Review ID**: stable identity of the logical review, independent of HEAD changes.
- **Snapshot**: immutable implementation identity reviewed at one point in time.
- **Round**: review of one implementation snapshot after the implementation changed or after the workflow deliberately starts a new semantic round.
- **Attempt**: repeated reviewer execution against the same immutable snapshot and same review contract.
- **Conversation Segment**: one physical ChatGPT Project conversation used to execute part or all of an attempt.
- **Checkpoint**: persisted authoritative PowerPack state required to resume the logical review.
- **Finding ID**: stable PowerPack-assigned identity for one material defect across rounds.
- **Finding Fingerprint**: deterministic matching aid based on stable semantic anchors; it is not the finding's identity by itself.
- **Continuation Packet**: deterministic prompt/input bundle used to resume the same attempt in another Project conversation.
- **Master Review Prompt**: versioned review-governance instruction that defines depth, evidence threshold and anti-round-trip behavior.
- **Review Protocol**: machine-validatable output/state contract used by PowerPack.
- **Review Divergence**: material conflict between valid attempts over the same immutable snapshot that cannot be reconciled automatically.

## User Scenarios & Testing

### User Story 1 — One review survives multiple GPT Web conversations (Priority: P1)

A maintainer starts an `implement-review` review in the bound ChatGPT Project. If the active conversation can no longer accept useful interaction, the maintainer opens another conversation in the same Project and resumes from a PowerPack-generated continuation packet.

**Acceptance Scenarios**:

1. Conversation rollover does not create a new logical review.
2. Conversation rollover does not increment the review round.
3. If the previous attempt was incomplete, the new conversation resumes the same attempt unless the user explicitly restarts it.
4. The continuation packet contains the authoritative checkpoint and open finding state.
5. The workflow remains valid even when previous Project conversations are unavailable to the model.

### User Story 2 — Review state survives separate PowerPack sessions (Priority: P1)

A maintainer closes the terminal/session and later resumes the same PR/SPEC review.

**Acceptance Scenarios**:

1. PowerPack resolves the existing review automatically from repository + PR + active SPEC.
2. The user is not required to remember a previous review JSON path.
3. The next execution loads the persisted checkpoint before generating reviewer input.
4. Missing Project-memory recall does not erase prior findings.

### User Story 3 — Previous findings cannot silently disappear (Priority: P1)

A prior valid review reported multiple findings. A later review must explicitly account for all relevant prior findings.

**Acceptance Scenarios**:

1. Every unresolved prior finding appears exactly once in the next lifecycle evaluation.
2. Absence of a prior finding is never equivalent to resolution.
3. Renaming or rewording a finding does not create a new identity when stable semantic anchors match the existing finding.
4. If the reviewer cannot determine the state of a prior finding, it remains unresolved or becomes `BLOCKED`, never silently resolved.

### User Story 4 — Same snapshot cannot magically resolve a finding (Priority: P1)

A finding exists for immutable snapshot `S`. The review is executed again against the exact same snapshot.

**Acceptance Scenarios**:

1. `RESOLVED` and `PARTIALLY_RESOLVED` transitions are rejected when no implementation snapshot change occurred.
2. A finding may remain `STILL_OPEN`.
3. A finding may become `INVALIDATED` only with evidence proving the previous finding itself was incorrect, duplicate, non-normative or based on a false assumption.
4. A new finding discovered on unchanged snapshot `S` is recorded as `NEWLY_DISCOVERED`, not as a regression caused by code change.

### User Story 5 — Changed code may resolve a finding only with repair evidence (Priority: P1)

A maintainer changes the implementation after a blocking finding.

**Acceptance Scenarios**:

1. A new HEAD produces a new immutable snapshot in the same logical review.
2. `RESOLVED` requires the specific repair delta, current implementation evidence and verification of the original failure scenario.
3. An unrelated code change cannot satisfy resolution evidence.
4. The complete new snapshot is reviewed again after prior findings are revalidated.

### User Story 6 — Repeated review attempts expose divergence instead of hiding it (Priority: P1)

Two valid review attempts over the same snapshot produce materially different blocker sets or verdicts.

**Acceptance Scenarios**:

1. The second attempt never overwrites the first attempt.
2. Findings from both attempts are reconciled against stable identity rules.
3. Material unresolved conflict yields `BLOCKED_REVIEW_DIVERGENCE`.
4. Divergence cannot be converted to `APPROVED` merely by selecting the more convenient attempt.

### User Story 7 — The review remains deep and anti-round-trip (Priority: P1)

The reviewer finds one blocker early in the review.

**Acceptance Scenarios**:

1. The reviewer continues through all required review fronts instead of returning immediately.
2. The reviewer performs a full-snapshot pass, not only a remediation-delta pass.
3. The reviewer performs an adversarial verdict challenge before approval.
4. The response consolidates independent findings so new rounds are primarily caused by implementation changes rather than an earlier review stopping early.

### User Story 8 — Findings require current normative authority (Priority: P1)

A reviewer proposes a broader architecture or best practice not required by the active contract.

**Acceptance Scenarios**:

1. A blocker without an identifiable current authority reference is rejected as a valid blocker.
2. General engineering preference, future capability ideas and reviewer taste cannot become blockers by themselves.
3. A valid finding identifies the violated SPEC requirement, acceptance criterion, explicit contract, project invariant or preserved baseline behavior.
4. New product intent must be promoted deliberately into durable authority before it can become implementation non-compliance.

### User Story 9 — Review works with current GPT Web limitations (Priority: P1)

The product does not expose a supported public API for PowerPack to create/append ChatGPT Project conversations.

**Acceptance Scenarios**:

1. The baseline flow does not depend on unsupported programmatic conversation writes.
2. PowerPack can generate a complete review/continuation packet for the user to paste into a Project conversation.
3. PowerPack can import and validate the structured result returned by the Web conversation.
4. A future official automation transport may replace the manual handoff without changing review-state semantics.

## Core State Model

### Review identity

Conceptually:

```text
review_id = canonical(repository, pull_request_number, spec_id, workflow="implement-review")
```

`head_sha` MUST NOT be part of `review_id` because implementation changes are expected during the lifecycle.

### Snapshot identity

Every attempt is bound to an immutable snapshot containing at minimum:

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

A deterministic `snapshot_sha256` MUST cover the implementation identity. A separate review-contract identity MAY cover protocol/prompt identity, but the persisted attempt MUST make both identities explicit.

### Lifecycle hierarchy

```text
Review
  Round 1 — Snapshot A
    Attempt 1
      Segment 1
      Segment 2 (rollover)
    Attempt 2 (same snapshot, repeat review)
  Round 2 — Snapshot B
    Attempt 1
      Segment 3
```

### Finding lifecycle

Allowed semantic states:

```text
NEW
NEWLY_DISCOVERED
STILL_OPEN
PARTIALLY_RESOLVED
RESOLVED
INVALIDATED
REGRESSED
```

Core transition constraints:

```text
same_snapshot + prior_open_finding
  => STILL_OPEN | INVALIDATED
  != RESOLVED
  != PARTIALLY_RESOLVED
```

```text
changed_snapshot + RESOLVED
  => repair_delta_evidence
  => current_implementation_evidence
  => original_failure_verification
```

```text
INVALIDATED
  => previous finding itself was wrong / duplicate / non-normative / assumption-invalid
  != implementation repair
```

A finding that was truly resolved and later materially reappears is `REGRESSED`.

## Master Review Prompt Contract

PowerPack MUST package a versioned master review prompt or equivalent immutable review-governance asset.

The master prompt MUST preserve the existing strong review properties:

- SPEC is normative authority; code is implementation; tests are evidence, not authority;
- complete normative-model construction before verdict;
- complete PR/blast-radius inspection;
- systemic invariant review rather than file-only review;
- crash/recovery analysis when applicable;
- idempotency analysis when applicable;
- concurrency analysis when applicable;
- persistence/schema analysis when applicable;
- state-machine analysis when applicable;
- non-happy-path coverage;
- test-quality and mock-strength review;
- architecture and cutover review;
- behavior-preservation review;
- evidence-backed severity;
- anti-round-trip full pass after first blocker;
- deterministic finding structure;
- unequivocal final verdict;
- complete re-review after implementation changes.

The generic master prompt MUST NOT hard-code domain-specific concerns such as trading, brokers or finance. Domain-specific concerns belong to the active SPEC, project durable context or explicit per-review special concerns.

The master prompt MUST additionally enforce review-lineage rules:

1. persisted checkpoint is authoritative for lifecycle state;
2. every prior finding must be explicitly revalidated;
3. same-snapshot attempts cannot resolve findings;
4. `INVALIDATED` requires evidence against the previous finding itself;
5. changed-snapshot resolution requires repair evidence;
6. new same-snapshot findings are `NEWLY_DISCOVERED`, not regressions;
7. blockers require a current authority reference;
8. material same-snapshot attempt disagreement must be surfaced, not hidden.

## Persistent Review Checkpoint

The implementation MUST persist state under a PowerPack-owned project-local review namespace. The technical plan defines exact paths and git-ignore/evidence policy.

Conceptual representation:

```json
{
  "schema_version": "3.0",
  "review_id": "owner/repo#15:001-single-skill-baseline:implement-review",
  "repository": "owner/repo",
  "pull_request_number": 15,
  "spec_id": "001-single-skill-baseline",
  "current": {
    "round": 4,
    "attempt": 2,
    "segment": 3,
    "head_sha": "<40-char-sha>",
    "snapshot_sha256": "<sha256>",
    "status": "ATTEMPT_IN_PROGRESS"
  },
  "protocol": {
    "version": "3.0",
    "sha256": "<sha256>"
  },
  "master_prompt": {
    "version": "2.0",
    "sha256": "<sha256>"
  },
  "findings": {
    "F-001": {"status": "RESOLVED"},
    "F-002": {"status": "STILL_OPEN"},
    "F-003": {"status": "INVALIDATED"}
  }
}
```

The checkpoint is workflow `STATE`, not immutable review `EVIDENCE`. Individual imported review results remain historical evidence and MUST NOT be overwritten.

## Conversation Rollover Contract

When the active ChatGPT Project conversation cannot continue effectively:

```text
active attempt
  -> mark segment ended/interrupted
  -> persist checkpoint
  -> create continuation packet
  -> user opens a new conversation in the same bound Project
  -> user pastes continuation packet
  -> review resumes same attempt or starts an explicit new attempt
```

Rollover MUST NOT implicitly increment `round`.

The continuation packet MUST contain at minimum:

```text
review_id
round
attempt
segment
snapshot identity
review-contract identity
last completed checkpoint
all open findings
prior finding lifecycle states
required output schema
instruction to continue the same logical review
```

The recommended visible conversation title is:

```text
[REVIEW] <SPEC-ID> / PR-<N> / <segment-number>
```

The title is a human convenience only and MUST NOT be used as workflow authority.

## Functional Requirements

- **FR-001**: SPEC-001A MUST be treated as an amendment to SPEC-001 and MUST NOT rewrite SPEC-001 historical content.
- **FR-002**: SPEC-001 + SPEC-001A MUST be the exclusive normative owner chain for `implement-review` semantics.
- **FR-003**: Later infrastructure/orchestration specs MUST NOT redefine `implement-review` states, finding semantics, approval semantics, provider semantics or budgets without explicitly amending this owner chain.
- **FR-004**: PowerPack MUST derive a stable `review_id` from repository, PR, active SPEC and workflow identity; HEAD MUST NOT be part of `review_id`.
- **FR-005**: Every reviewer attempt MUST bind to one immutable implementation snapshot and one explicit review-contract identity.
- **FR-006**: Snapshot identity MUST include exact PR/base/head/merge-base/changed-file and active-SPEC identity sufficient to prevent review substitution.
- **FR-007**: Review artifacts MUST record master-prompt and review-protocol version/digest so comparable attempts can prove which contract they used.
- **FR-008**: PowerPack MUST persist review lineage independently from ChatGPT Project memory/conversation continuity.
- **FR-009**: An existing lineage for the same repository + PR + SPEC MUST be resumed automatically unless the user explicitly starts a new logical review.
- **FR-010**: Manual `--previous <file>` MAY remain as an escape hatch/import aid but MUST NOT be the primary continuity mechanism.
- **FR-011**: One logical review MAY span multiple ChatGPT Project conversations.
- **FR-012**: Conversation rollover MUST NOT increment the review round or silently restart finding state.
- **FR-013**: PowerPack MUST generate a deterministic continuation packet sufficient to resume without relying on Project memory.
- **FR-014**: The baseline implementation MUST NOT require an unsupported public API for creating or appending ChatGPT Project conversations.
- **FR-015**: The baseline implementation MUST support importing a structured review result produced in the bound ChatGPT Project conversation.
- **FR-016**: Review result import MUST validate review id, snapshot identity, review-contract identity, schema and prior-finding accounting before mutating lifecycle state.
- **FR-017**: Every prior unresolved or historically relevant finding MUST be explicitly accounted for in each later lifecycle evaluation.
- **FR-018**: Prior finding omission MUST be a validation error, not implicit resolution.
- **FR-019**: Finding identity MUST be stable across wording/line-number drift and MUST NOT depend primarily on natural-language title or source line number.
- **FR-020**: A persisted immutable finding ID MUST be assigned once; deterministic fingerprints are matching aids only.
- **FR-021**: Stable finding matching SHOULD use authority reference, category, repository-relative path, logical symbol/component and normalized failure-mode signature where available.
- **FR-022**: On an unchanged snapshot, `RESOLVED` and `PARTIALLY_RESOLVED` transitions MUST be rejected.
- **FR-023**: On an unchanged snapshot, `INVALIDATED` is permitted only with evidence showing the prior finding itself was incorrect, duplicate, non-normative or assumption-invalid.
- **FR-024**: A finding discovered for the first time on an unchanged snapshot MUST be marked `NEWLY_DISCOVERED`; it MUST NOT be described as a code regression caused by a nonexistent implementation change.
- **FR-025**: On a changed snapshot, `RESOLVED` MUST identify a relevant repair delta, current implementation evidence and verification against the original failure scenario.
- **FR-026**: An unrelated implementation delta MUST NOT satisfy resolution evidence.
- **FR-027**: A finding previously resolved and later materially reintroduced MUST be reported as `REGRESSED`.
- **FR-028**: Multiple valid attempts against the same immutable snapshot MUST be preserved as separate evidence artifacts.
- **FR-029**: Material conflicts between same-snapshot attempts over blocker existence, prior-finding state or final verdict MUST be reconciled explicitly or yield `BLOCKED_REVIEW_DIVERGENCE`.
- **FR-030**: A later attempt MUST NOT silently overwrite or erase findings from an earlier valid attempt.
- **FR-031**: The reviewer MUST execute a complete review of the immutable snapshot after prior findings are revalidated; remediation-delta-only review is insufficient.
- **FR-032**: The reviewer MUST continue through all mandatory review fronts after discovering a blocker so the result is a consolidated finding set whenever possible.
- **FR-033**: The reviewer MUST perform an adversarial verdict challenge before `APPROVED`.
- **FR-034**: Every blocking finding MUST identify at least one current normative authority reference.
- **FR-035**: Generic best practice, hypothetical future capability or reviewer preference alone MUST NOT be sufficient authority for a blocker.
- **FR-036**: Every finding MUST include authority reference, implementation evidence, deterministic/causal failure scenario, actual behavior, required behavior, impact, required correction and verifiable acceptance criteria.
- **FR-037**: If evidence is insufficient to responsibly determine compliance, the review MUST return a blocking/blocked state rather than inventing approval or a speculative blocker.
- **FR-038**: The generic master review prompt MUST be a versioned PowerPack asset and MUST avoid unrelated domain-specific assumptions.
- **FR-039**: Per-project or per-review special concerns MAY extend the generic prompt only when they are grounded in durable project authority or explicit user instruction.
- **FR-040**: Review round budget semantics belong to SPEC-001A and MUST be independent from checklist-converge budgets.
- **FR-041**: Budget exhaustion with unresolved findings or unresolved divergence MUST block; exhaustion MUST NOT imply approval.
- **FR-042**: Any implementation change that changes the immutable snapshot invalidates approvals tied to the previous snapshot.
- **FR-043**: Final approval requires every mandatory gate applicable to `implement-review` to approve the same final immutable snapshot.
- **FR-044**: `APPROVED` additionally requires zero unresolved findings, zero unresolved prior-finding accounting gaps, zero material review divergence, complete required evidence coverage and a successful adversarial verdict challenge.
- **FR-045**: ChatGPT Project memory and historical Project conversations MAY enrich reviewer context but MUST NOT be the sole source of review continuation state.
- **FR-046**: Deleting, archiving, branching or exhausting a ChatGPT conversation MUST NOT corrupt the persisted logical review.
- **FR-047**: The technical design MUST distinguish mutable review `STATE` from immutable review `EVIDENCE` and durable user `CONFIG`.
- **FR-048**: When SPEC-002 generic state/registry/doctor infrastructure is available, SPEC-001A SHOULD consume it without delegating capability-specific semantics back to SPEC-002.
- **FR-049**: `implement-review` capability readiness MAY consume environment facts discovered by SPEC-002 infrastructure, but the readiness decision and failure semantics remain owned by SPEC-001A.
- **FR-050**: The implementation MUST provide deterministic contract tests for same-snapshot monotonicity, prior-finding completeness, finding identity stability, resolution evidence, rollover continuity and divergence handling.

## PR15 Review Maturity Extensions

This section is a normative amendment derived from repeated review rounds of PR15. It strengthens the evidence and merge-gate protocol without changing the ownership boundary already established by SPEC-001A.

### PR15-001 — Review Readiness Gate

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

### PR15-002 — Requirement Traceability Contract

Every normative requirement selected for the review MUST be traceable through:

```text
requirement
  -> implementation evidence
  -> validation/test evidence
  -> observed result
```

A machine-readable traceability matrix SHOULD expose requirement ID, statement, implementation files/symbols, validation tests/commands and status. A requirement without sufficient implementation or validation evidence MUST be classified as a verification gap rather than inferred to be compliant.

### PR15-003 — Three-Phase Review Model

The lifecycle MUST distinguish:

1. **Context Integrity Review** — prove repository, PR, snapshot, active SPEC, changed files and review-contract identity.
2. **Implementation Correctness Review** — evaluate implementation behavior, architecture, invariants, failure modes, persistence, concurrency, recovery and test quality as applicable.
3. **SPEC Compliance Merge Gate** — reconcile every requirement, prior finding, blocker, evidence gap and verdict against the same final immutable snapshot.

A substantive verdict MUST NOT be emitted from an incomplete Context Integrity Review.

### PR15-004 — Finding Classification

Every material observation MUST have one primary classification:

```text
BUG
SPEC_VIOLATION
VERIFICATION_GAP
ARCHITECTURE_RISK
ENHANCEMENT
FUTURE_CAPABILITY
```

Only `BUG`, `SPEC_VIOLATION` and blocking `VERIFICATION_GAP` findings MAY block the merge gate when their blocking criteria are satisfied. `ENHANCEMENT` and `FUTURE_CAPABILITY` MUST NOT become blockers merely because they are desirable. `ARCHITECTURE_RISK` MUST identify the violated current authority or invariant before becoming a blocker.

### PR15-005 — Evidence-First Blocking

A blocker MUST contain:

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

A blocker MUST NOT be based solely on intuition, generic best practice, future design preference or an unverified interpretation of the SPEC.

### PR15-006 — Anti-Roundtrip Full-Pass Rule

Finding the first blocker MUST NOT terminate the substantive review.

After identifying a blocker, the reviewer MUST continue through all mandatory review fronts and consolidate independent findings before returning the result. At minimum:

```text
full changed-file pass
full requirement/acceptance pass
blast-radius/invariant pass
non-happy-path pass
regression/behavior-preservation pass
adversarial verdict challenge
```

A later review round SHOULD therefore be caused primarily by implementation changes or newly available authoritative evidence, not by a reviewer stopping after the first defect.

### PR15-007 — Self-Validation Before Review

The implementation owner SHOULD provide a PR self-validation declaration before requesting substantive review:

```yaml
implementation_ready: true
spec_mapped: true
tests_added_or_verified: true
changed_files_known: true
evidence_complete: true
```

A failed self-validation MUST be surfaced as `NOT_READY_FOR_REVIEW` or an equivalent context state instead of being disguised as an implementation defect.

### PR15-008 — Immutable Changed-File Coverage

`coverage.changed_files` MUST contain the complete changed-file set for the immutable snapshot under review. A coverage mismatch is a context-integrity failure and MUST block the merge gate until reconciled.

### PR15-009 — Contract Tests for Review Readiness

The implementation MUST add or maintain deterministic tests for incomplete Evidence Package rejection, changed-file coverage mismatch, requirement-to-evidence traceability gaps, finding classification validation, blocker authority validation, anti-roundtrip full-pass behavior, prior-finding completeness, same-snapshot monotonicity, changed-snapshot resolution evidence, same-snapshot divergence and continuation/recovery behavior.

### PR15-010 — Review Quality Metrics

The lifecycle SHOULD expose:

```text
review_round_count
review_attempt_count
context_block_count
evidence_missing_count
finding_reopen_count
finding_resolution_count
same_snapshot_divergence_count
```

These are process-quality signals and MUST NOT themselves determine approval.

### PR15-011 — Recurring Finding to SPEC Evolution

When a review repeatedly identifies the same process-level deficiency across independent PRs or review rounds, the deficiency MUST be evaluated as a possible specification/process gap.

Preferred evolution:

```text
recurring review failure
  -> process gap
  -> durable normative rule
  -> SPEC amendment
  -> future PR inheritance
```

The same deficiency MUST NOT be rediscovered indefinitely as an ad-hoc reviewer comment.

### PR15-012 — Scope-Control Rule

A review MUST distinguish:

```text
current contract violation
current verification failure
architecture risk against current authority
future capability
engineering preference
```

Only the first three categories can become blocking findings, and only with evidence satisfying the blocker contract.

### PR15-013 — Final Approval Preconditions

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

### PR15-014 — Review Evidence Manifest

The implementation SHOULD generate a manifest similar to:

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

### PR15-015 — Added Invariants

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

## Required Contract Tests

At minimum, automated tests MUST prove:

| Scenario | Required result |
|---|---|
| Same HEAD, previous open finding present | finding cannot become `RESOLVED` |
| Same HEAD, reviewer omits previous finding | result rejected |
| Same HEAD, prior finding proven incorrect | `INVALIDATED` allowed with evidence |
| New HEAD, unrelated delta | `RESOLVED` rejected |
| New HEAD, relevant repair + verification | `RESOLVED` allowed |
| Same defect reworded / line changed | previous finding identity retained |
| New chat during same attempt | round unchanged |
| New PowerPack process/session | lineage recovered |
| Second attempt adds blocker on same HEAD | blocker accumulated; prior findings retained |
| Two same-snapshot attempts materially conflict | reconcile or `BLOCKED_REVIEW_DIVERGENCE` |
| Project memory omits historical conversation | continuation remains correct from checkpoint |
| Conversation limit reached | continuation packet resumes without losing round/finding state |
| Master prompt/protocol digest differs | attempts are not treated as contract-equivalent without explicit handling |
| Blocking finding has no authority reference | result rejected as invalid blocker |
| Evidence Package is incomplete | review blocked before substantive review |
| Changed-file coverage is incomplete | review blocked as context-integrity failure |
| Requirement has no validation evidence | verification gap, not inferred compliance |
| First blocker is found early | reviewer completes mandatory review fronts before verdict |

## Success Criteria

- **SC-001**: Repeating a review on an unchanged snapshot produces zero accepted `RESOLVED`/`PARTIALLY_RESOLVED` transitions for previously open findings.
- **SC-002**: 100% of prior unresolved finding IDs are explicitly accounted for in every valid subsequent review result.
- **SC-003**: Conversation rollover preserves the same `review_id`, round and unresolved finding set in deterministic contract tests.
- **SC-004**: Restarting PowerPack in a separate process/session recovers the same logical review without manually passing a previous-result path.
- **SC-005**: Rewording/title/line drift fixtures do not create duplicate identities for the same material finding when stable anchors still match.
- **SC-006**: Same-snapshot conflicting-attempt fixtures never produce silent approval; they reconcile explicitly or return `BLOCKED_REVIEW_DIVERGENCE`.
- **SC-007**: Every accepted blocker contains a valid current authority reference and complete required evidence fields.
- **SC-008**: A generic review fixture from a non-trading/non-financial domain receives zero domain-specific review requirements solely from the packaged master prompt.
- **SC-009**: A full review can be resumed in a new ChatGPT Project conversation using only the generated continuation packet plus the current authoritative repository/PR evidence.
- **SC-010**: No supported baseline path requires private/undocumented ChatGPT conversation-write APIs.
- **SC-011**: SPEC-002 and SPEC-003 can be implemented/reviewed without acting as competing normative owners of `implement-review` semantics.
- **SC-012**: A substantive review cannot begin when required immutable review context is missing.
- **SC-013**: Every blocking finding accepted by the merge gate contains the required authority and evidence fields.
- **SC-014**: Contract tests prove that finding the first blocker does not terminate the mandatory review pass.
- **SC-015**: Repeated process deficiencies can be encoded as durable review/SPEC rules rather than requiring repeated ad-hoc review comments.

## Assumptions

- The bound ChatGPT Project supports user-created conversations and access to the configured GitHub connector.
- ChatGPT Project conversations have practical interaction/context limits that PowerPack cannot remove.
- Project memory is useful but not deterministic enough to serve as the authoritative workflow ledger.
- A human-in-the-loop copy/paste/import step is acceptable for the baseline GPT Web transport when no supported conversation-write API exists.
- Model outputs are probabilistic; reproducibility therefore means stable authoritative inputs, lifecycle constraints and reconcilable state, not byte-identical prose.
- SPEC-002 may later provide shared state/registry/doctor infrastructure, but this specification remains the semantic owner of `implement-review`.

## Non-Goals

- Guaranteeing byte-identical LLM output across repeated executions.
- Eliminating all possible false-positive/false-negative model judgments.
- Programmatically bypassing ChatGPT Web usage/context limits.
- Depending on private/unsupported ChatGPT conversation-write endpoints.
- Reintroducing capabilities removed by SPEC-001.
- Redefining `checklist-converge` semantics.
- Owning generic plugin installation, bundle lifecycle, capability registry internals or generic doctor behavior that belong to SPEC-002.
- Defining the global order in which future PowerPack capabilities are orchestrated; future orchestration specs own stage ordering while respecting capability boundaries.

## Core Invariants

```text
implement-review semantic owner == SPEC-001 + SPEC-001A
```

```text
logical_review != chatgpt_conversation
```

```text
review_id != snapshot_id
```

```text
conversation_rollover
  => same logical review
  => same round unless explicitly advanced
```

```text
same_snapshot + prior_open_finding
  != RESOLVED
  != PARTIALLY_RESOLVED
```

```text
RESOLVED
  => changed_snapshot
  => relevant_repair_delta
  => current_evidence
  => original_failure_verified
```

```text
INVALIDATED
  => previous_finding_was_wrong
  != code_fix
```

```text
previous_finding_absent
  != resolved
```

```text
same_snapshot_attempt_conflict
  => explicit_reconciliation | BLOCKED_REVIEW_DIVERGENCE
  != silent_overwrite
```

```text
blocking_finding
  => current_authority_ref
  => concrete_evidence
```

```text
PROJECT_MEMORY == supplemental_context
POWERPACK_CHECKPOINT == review_lifecycle_authority
```

```text
CONFIG != STATE != EVIDENCE
```

```text
future_infrastructure_or_orchestration
  != capability_semantic_owner
```

```text
review_start
  => context_integrity_proven
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
