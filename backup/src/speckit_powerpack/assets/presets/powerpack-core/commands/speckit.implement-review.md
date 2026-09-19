---
description: "Specify PowerPack implementation-quality convergence/review gate after an explicit speckit-implement."
---

# Spec Kit Implement Review

This Specify PowerPack command reviews, converges and stabilizes an implementation **already produced by an explicit `speckit-implement`**.

Happy path:

```text
speckit-analyze
  -> speckit-implement
  -> speckit-implement-review
       -> speckit-converge
       -> capability-selected quality gate
       -> independent Sol/xhigh review
       -> browserless ChatGPT Project + GitHub review
       -> both gates approve the same immutable snapshot
       -> COMPLETE
```

`implement-review` never performs the initial implementation merely to satisfy its own prerequisite.

## Invariants

Always use:

```text
DISCOVER CAPABILITY -> SELECT STRATEGY -> EXECUTE CONTRACT
```

Do not hard-code project language/build behavior. Do not silently switch reviewer, Project, GitHub repository or PR after a failure.

The browserless Project/GitHub reviewer is read-only and uses:

```text
~/.codex/auth.json
  -> ChatGPT Project backend reads
  -> serialized Project context
  -> explicit [$github](app://<connector-id>)
  -> codex exec --json --ephemeral --sandbox read-only
  -> codex_apps MCP
  -> GitHub tool calls/results
```

It does **not** use Chrome, CDP, Playwright, Web2API, copied cookies or browser profiles.

## Mandatory readiness

Before convergence/review:

```bash
specify-powerpack doctor . --strict-review
specify-powerpack review status --path . --live
```

Readiness requires:

- official Spec Kit project and Specify PowerPack runtime installed;
- Codex CLI on `PATH` and `codex login` completed;
- repository bound to one ChatGPT Project;
- GitHub App/connector installed, OAuth active and repository access authorized;
- `review_backend = codex-apps-github`.

Failure is `BLOCKED_CONFIGURATION`. There is no browser fallback.

## Mandatory predecessor

Run:

```bash
python .specify/powerpack/bin/powerpack.py prereq check --step implement-review
```

If it fails, STOP and return to `speckit-implement`. A receipt from another SPEC never satisfies this prerequisite.

## Phase 1 — convergence

Run `speckit-converge` for the same active SPEC. Use the configured convergence budget (default 5).

- `CONVERGED` -> continue;
- tasks appended -> run `speckit-implement` for exactly that authorized work, then converge again;
- owner/product decision -> return to the responsible earlier stage;
- budget exhausted -> `BLOCKED_BUDGET`.

## Quality gate

Use capability discovery, not language-specific assumptions:

```bash
python .specify/powerpack/bin/capabilities.py gate detect
python .specify/powerpack/bin/capabilities.py gate run
```

Unknown/ambiguous architectures fail closed unless project configuration defines a deterministic custom gate. Documentation-only deltas may be `NOT_APPLICABLE` when correctly justified.

## Independent Sol review

The semantic reviewer contract is `gpt-5.6-sol/xhigh/read-only`. Follow the executor-aware route returned by:

```bash
python .specify/powerpack/bin/powerpack.py review route
```

Do not create recursive reviewer chains. Sol findings are mandatory work; the implementer fixes them and convergence/quality gates run again.

## Browserless Project + GitHub deep review

This gate is mandatory after Sol is clean.

The GitHub PR must already exist and must correspond to the current local HEAD. Run:

```bash
specify-powerpack review run \
  --path . \
  --pr <number-or-canonical-github-pr-url> \
  --prompt "Perform the complete Deep Review Evidence Protocol."
```

Optional round-2+ continuity:

```bash
specify-powerpack review run \
  --path . \
  --pr <pr> \
  --previous <previous-review.json> \
  --output <review.json>
```

### Phase A — immutable PR manifest

Specify PowerPack first asks the selected GitHub App to resolve:

- exact repository and PR number;
- base ref and full base SHA;
- merge-base;
- full head SHA;
- complete changed-file list.

Specify PowerPack then:

1. verifies local `HEAD == PR head SHA`;
2. resolves exactly one active Spec Kit SPEC from the current branch;
3. computes a deterministic SHA-256 snapshot digest over PR identity, SPEC id and changed files.

A mismatch blocks review before a verdict can be emitted.

### Phase B — deep review

Specify PowerPack serializes:

- bound ChatGPT Project metadata/instructions and recent Project conversations;
- active Spec Kit artifacts (`spec.md`, plan/tasks/research/data-model/quickstart/contracts/checklists);
- the immutable PR manifest;
- Deep Review Protocol 2.0;
- previous findings when provided.

Codex receives an explicit GitHub App mention and must inspect the exact PR/diff/files through `codex_apps` MCP. Specify PowerPack rejects a run if it observes shell or web-search fallback, no GitHub tool call/result, a different snapshot, incomplete changed-file coverage, or missing literal Project-context evidence.

Reviewer output must be one schema `2.0` JSON object and cover all mandatory fronts:

- `SPEC_COMPLIANCE`
- `BEHAVIORAL_REGRESSION`
- `ARCHITECTURE_AND_CONTRACTS`
- `STATE_CONCURRENCY_AND_FAILURES`
- `PERSISTENCE_DETERMINISM_IDEMPOTENCY`
- `TESTS_AND_COMPOSITION_ROOT`
- `DOCUMENTATION_AND_OPERABILITY`
- `SECURITY_AND_SCOPE`

Specify PowerPack validates the artifact with:

```bash
python .specify/powerpack/bin/review_protocol.py validate --input <review.json>
```

Round 2+ also validates against `--previous`.

`APPROVED` requires no findings and complete protocol coverage. `CHANGES_REQUIRED` findings are mandatory work; `BLOCKED` is never converted to approval.

## Findings repair loop

For every finding:

```text
finding
  -> implement fix
  -> converge
  -> capability quality gate
  -> fresh Sol review
  -> fresh Project+GitHub review
```

Any implementation change invalidates approvals tied to the prior head/snapshot digest. Final approvals must refer to the same final snapshot.

## Completion

Complete only when:

1. explicit same-SPEC initial `speckit-implement` predecessor is proven;
2. convergence is clean;
3. all findings are resolved with evidence;
4. quality gate passed or is correctly `NOT_APPLICABLE`;
5. independent Sol/xhigh review approves;
6. browserless ChatGPT Project + GitHub review approves the exact same snapshot.

Return:

```text
Stage Handoff: COMPLETE
Próxima etapa: nenhuma
```

Use `BLOCKED_CONFIGURATION` for missing Codex/Project/GitHub readiness, `BLOCKED_BUDGET` for exhausted rounds, and `BLOCKED` for reviewer inability. Never merge/approve a PR, force-push or reset destructively without a separate explicit user instruction.
