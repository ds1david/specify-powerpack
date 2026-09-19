# Specify PowerPack Deep Review Evidence Protocol

## Purpose

Determine, with reproducible evidence, whether the current implementation snapshot satisfies the active SPEC without introducing regressions outside the requested scope. A review is a technical quality gate, not a style pass and not a source of optional backlog suggestions.

Every review round is bound to one immutable snapshot identity: SPEC, base SHA, merge-base, head SHA and snapshot digest. Previous approvals, green CI, PR descriptions and implementer claims are hypotheses, never proof.

The supported browserless provider materializes that identity from the exact GitHub PR through the selected GitHub App and then verifies local `HEAD == PR head SHA`. Do not substitute a different repository, PR, branch or local-only approximation.

## Review scope: defect versus capability expansion

Specify PowerPack is a personal project in continuous evolution and is progressively generalized into a reusable plugin for projects of different domains and technical contexts. That evolution must not turn product ideation into blocking review findings.

A finding is valid when there is concrete evidence that the reviewed snapshot violates the current contract, for example:

- an active SPEC requirement or acceptance criterion is not satisfied;
- documented behavior or an explicit contract is broken;
- a non-weakenable Specify PowerPack invariant is violated;
- behavior expected to be preserved has regressed;
- an already-supported capability behaves incorrectly, inconsistently or unsafely.

A request to support a new provider, platform, workflow, architecture, convenience behavior or broader generalization is normally a capability proposal, not a defect, until it is deliberately promoted into the active SPEC or another durable repository contract.

A reviewer MUST NOT block approval solely because a broader design would be useful. Every finding must identify the current requirement, contract, invariant or preserved behavior that is actually violated.

## Required evidence order

Read, when present, in this order:

1. the immutable PR snapshot and review context;
2. project instructions and constitution/policies;
3. the active SPEC artifacts (`spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`, `checklists/`);
4. the complete diff against the merge-base and complete contents of every changed file;
5. callers, callees, implementations, schemas, migrations, configuration and tests necessary to establish blast radius;
6. the previous round only to verify prior findings, never to inherit its conclusion.

`coverage.changed_files` MUST exactly match the immutable PR changed-file set. Every changed file MUST appear in `coverage.inspected_files` and MUST have concrete `coverage.inspection_evidence`.

## Requirement completeness

When the active SPEC exposes requirement IDs such as `FR-*`, `NFR-*`, `REQ-*`, `SC-*`, `AC-*` or `UC-*`, `coverage.requirements` MUST contain exactly that same set of IDs.

A non-empty subset is not sufficient. If one requirement cannot be evaluated, return `PARTIAL`, `FAIL` or `BLOCKED` with evidence instead of omitting it.

## Mandatory review fronts

The reviewer must cover all fronts and attach concise concrete evidence to each:

1. `SPEC_COMPLIANCE` — requirements, acceptance scenarios, success criteria and tasks map to implementation and tests/proof.
2. `BEHAVIORAL_REGRESSION` — compare baseline and head across happy path, validation, errors, replay/retry, restart, shutdown and side effects where applicable.
3. `ARCHITECTURE_AND_CONTRACTS` — boundaries, dependency direction, public contracts, schemas, migrations, serialization and compatibility.
4. `STATE_CONCURRENCY_AND_FAILURES` — ownership, transitions, TOCTOU, races, idempotency, retries, ordering, partial failure, rollback and resource cleanup.
5. `PERSISTENCE_DETERMINISM_IDEMPOTENCY` — transaction boundaries, constraints, read/write consistency, stable ordering, time/random/UUID effects, replay and restart determinism where applicable.
6. `TESTS_AND_COMPOSITION_ROOT` — tests can fail for the defect they claim to cover, negative/concurrent cases are represented, mocks do not hide behavior and the feature is reachable in the real composition root.
7. `DOCUMENTATION_AND_OPERABILITY` — diagnostics, logs, metrics, runbooks, documentation, performance and operational behavior affected by the change.
8. `SECURITY_AND_SCOPE` — authentication/authorization, secret handling, validation, injection/deserialization/path traversal risks and unrelated scope creep.

`NOT_APPLICABLE` is allowed only with concrete evidence explaining why the front does not apply.

## Procedure for every round

### Pass 1 — previous findings

On round 2+, validate every finding from the immediately previous review against the current head. Report each prior ID exactly once as one of:

- `RESOLVED`
- `PARTIALLY_RESOLVED`
- `NOT_RESOLVED`
- `REGRESSED`

Do not silently drop or rename previous IDs. A repeated material defect after it was claimed resolved is a repeated-finding condition and must be surfaced explicitly to the Specify PowerPack loop.

### Pass 2 — full snapshot review

Discard the previous verdict and review the entire current immutable snapshot again against the merge-base. Do not review only the correction delta.

For every relevant production flow, inspect when applicable:

```text
input -> validation -> decision -> persistence/effect -> observability -> failure/recovery
```

For concurrent state, identify ownership, valid transitions and the synchronization/linearization point.

### Pass 3 — adversarial verdict challenge

Before returning the verdict, actively try to invalidate it. Look for the strongest remaining counterexample in concurrency, replay, restart, partial failure, boundaries, constraints, side effects, shutdown, composition root, security and vacuously green tests.

Return the challenge in `coverage.verdict_challenge`:

```json
{
  "strongest_counterexample": "concrete failure hypothesis",
  "result": "SURVIVED",
  "evidence": ["specific evidence that defeats or confirms the hypothesis"]
}
```

Allowed challenge results:

- `SURVIVED`
- `FINDING`
- `BLOCKED`
- `NOT_APPLICABLE`

`APPROVED` requires `SURVIVED` or evidence-backed `NOT_APPLICABLE`.

## Inspection evidence

Every changed file requires one `coverage.inspection_evidence` entry:

```json
{
  "file": "path/to/file",
  "evidence": "what was inspected and why it proves the relevant behavior"
}
```

Merely listing a path in `inspected_files` is not proof of review coverage.

## Context-gap discipline

Every review MUST return:

```json
"context_gaps": []
```

inside `coverage`.

If serialized ChatGPT Project context contains a material architectural or product constraint that is absent from repository evidence, describe it in `coverage.context_gaps` and do **not** approve.

A Project-only constraint is not automatically a bug. First determine whether it belongs to the current contract. If it is a new requirement, promote it deliberately into `spec.md`, `research.md`, an ADR, architecture documentation or project policy before treating its absence as implementation non-compliance.

## Finding discipline

Every concrete defect is a finding regardless of severity. Findings are work for the current implementation-review loop and MUST NOT be converted to technical debt, backlog, TODO or future issue to obtain convergence.

A finding must include:

- `id`
- `severity`
- `category`
- `title`
- `file`
- `line`
- `evidence`
- `failure_scenario`
- `behavioral_impact`
- `required_change`
- `acceptance_criteria`

For `CHANGES_REQUIRED`, every finding must describe a concrete failure, observable impact and verifiable acceptance criteria rather than personal preference.

If context, tooling or infrastructure limitations prevent a responsible conclusion, use `BLOCKED`; do not approve by absence of evidence.

## Browserless GitHub evidence boundary

PR/repository evidence MUST come through the explicitly selected GitHub App in the Codex Apps MCP runtime.

The supported provider requires structural GitHub tool-call/result evidence. Shell commands, generic web search, PR descriptions, green CI or Project memory alone cannot satisfy GitHub review evidence.

Review is read-only. Never merge, approve, ready-for-review, force-push or otherwise mutate the PR as part of this protocol.

## Output contract

Return one JSON object using schema `2.0` with `review_context`, `coverage`, all mandatory fronts and `findings`.

`coverage` must include at least:

```json
{
  "changed_files": [],
  "inspected_files": [],
  "requirements": [],
  "baseline_scenarios": [],
  "previous_findings": [],
  "fronts": [],
  "inspection_evidence": [],
  "verdict_challenge": {},
  "context_gaps": []
}
```

Allowed requirement statuses: `PASS`, `PARTIAL`, `FAIL`, `NOT_APPLICABLE`.
Allowed baseline results: `PRESERVED`, `CHANGED_AS_SPECIFIED`, `REGRESSION`, `NOT_APPLICABLE`.
Allowed front statuses: `PASS`, `FINDINGS`, `BLOCKED`, `NOT_APPLICABLE`.

`APPROVED` requires all of the following:

- `findings: []`;
- exact immutable changed-file coverage;
- every changed file inspected;
- concrete inspection evidence for every changed file;
- exact requirement-ID coverage when requirement IDs are present;
- no requirement in `PARTIAL/FAIL`;
- no baseline `REGRESSION`;
- every previous finding `RESOLVED`;
- every front `PASS/NOT_APPLICABLE`;
- successful adversarial verdict challenge;
- `coverage.context_gaps: []`.

The installed validator is authoritative for the transport-independent structural contract, while the browserless provider additionally validates exact GitHub snapshot identity, exact SPEC requirement IDs and literal ChatGPT Project-context evidence:

```bash
python .specify/powerpack/bin/review_protocol.py validate --input <review.json>
python .specify/powerpack/bin/review_protocol.py validate --input <review.json> --previous <previous-review.json>
```
