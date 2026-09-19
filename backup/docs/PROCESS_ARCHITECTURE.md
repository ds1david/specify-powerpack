# Process architecture

## Product boundary

Specify PowerPack is an enhancement layer over official GitHub Spec Kit. Spec Kit owns specification artifacts and its canonical workflow; Specify PowerPack adds convergence, state, review evidence, technical-debt governance, model routing and installation/update support.

Canonical flow:

```text
speckit-specify
→ speckit-clarify
→ speckit-plan
→ speckit-checklist
→ speckit-checklist-converge
→ speckit-tasks
→ speckit-analyze
→ speckit-implement
→ speckit-implement-review
```

## Runtime architecture

```text
project repository
  ├─ Spec Kit artifacts
  ├─ .specify/powerpack policy/runtime
  └─ Git origin
          │
          ▼
Specify PowerPack CLI
  ├─ install/update/doctor
  ├─ Project binding
  ├─ GitHub connector discovery
  └─ browserless review provider
          │
          ├─ ChatGPT backend reads
          │    └─ serialized ChatGPT Project context
          │
          └─ codex exec --ephemeral --sandbox read-only
               └─ codex_apps MCP
                    └─ GitHub App/connector
```

Specify PowerPack does not use Chrome, Playwright, CDP or ChatGPT-Web2API in the supported runtime.

## Project context

The ChatGPT Project is not attached natively to the Codex review turn. Specify PowerPack reads Project metadata and a bounded number of recent Project conversations through the account-scoped ChatGPT backend, serializes that material, and passes it as read-only background context.

Therefore:

- `native_binding = false`;
- Project context is useful history, not authoritative current-code evidence;
- SPEC + immutable GitHub PR evidence override conflicting Project memory;
- the reviewer must return literal Project-context evidence so Specify PowerPack can prove the serialized context was consumed.

## GitHub capability

Specify PowerPack first discovers the GitHub plugin/connector through the account-scoped ChatGPT backend and requires enabled/authorized/available state. It then passes the resolved connector internally to Codex as an explicit `app://` mention.

The PR-reading model must use the `codex_apps` MCP surface. Specify PowerPack parses Codex JSONL and requires completed MCP tool calls with results. Command execution and web-search fallbacks are forbidden for GitHub evidence.

Connector/plugin IDs are operational identifiers and are redacted from normal reports.

## Immutable two-phase PR review

### Phase 1 — manifest

A read-only Codex App turn resolves exactly one explicit PR and returns:

- repository;
- PR number;
- base ref;
- full base SHA;
- merge base;
- full head SHA;
- complete changed-file list.

Specify PowerPack combines this with exactly one active Spec Kit SPEC and calculates a deterministic SHA-256 snapshot digest.

Before proceeding, local `HEAD` must equal the PR head SHA.

### Phase 2 — deep review

A second ephemeral read-only turn receives:

- immutable snapshot;
- serialized Project context;
- active SPEC context;
- Deep Review Protocol;
- optional previous review;
- user instruction.

It must inspect the exact PR through GitHub tools and return schema 2.0 JSON only.

Specify PowerPack verifies snapshot identity, exact changed-file coverage, Project-context evidence and the installed review-protocol validator.

## Fail-closed classifications

The implementation refuses to approve when it cannot prove the requested context. Examples include:

- ambiguous/missing SPEC;
- PR repository mismatch;
- local HEAD / PR head mismatch;
- unavailable GitHub App;
- GitHub MCP tool evidence missing;
- shell/web-search fallback observed;
- incomplete changed-file coverage;
- Project context not proven;
- invalid Deep Review Protocol output.

## Security boundary

Raw authentication secrets are never persisted to project files. Specify PowerPack reuses the Codex-authenticated account through its existing auth store. Review turns are ephemeral and read-only. The review provider never authorizes merge, PR approval, ready-for-review, force-push or destructive Git operations.

See [`DECISIONS_AND_TRADEOFFS.md`](DECISIONS_AND_TRADEOFFS.md) for rationale.
