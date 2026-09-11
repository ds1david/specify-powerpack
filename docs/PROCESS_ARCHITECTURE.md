# Process architecture

## Product boundary

Specify PowerPack is an enhancement layer over official GitHub Spec Kit. Spec Kit owns specification artifacts and its canonical workflow; Specify PowerPack adds one command, `speckit-implement-review` — an evidence-validated review gate that drives convergence (through upstream `speckit-converge`), quality gates, an independent Sol review and a browserless GitHub PR review — plus the model-routing and installation/update support it needs.

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
          └─ Sentinel PoW/Turnstile requirements
               └─ ChatGPT Web conversation SSE
                    ├─ dynamic Project gizmo binding
                    ├─ dynamic GitHub connector hint
                    └─ JIT allow continuation
```

Specify PowerPack does not use Chrome, Playwright, CDP or ChatGPT-Web2API in the supported runtime.

## Project context

The ChatGPT Project is not attached natively to the Codex review turn. Specify PowerPack reads Project metadata and a bounded number of recent Project conversations through the account-scoped ChatGPT backend, serializes that material, and passes it as read-only background context.

Therefore:

- `native_binding = false`;
- Project context is useful history, not authoritative current-code evidence;
- SPEC + immutable GitHub PR evidence override conflicting Project memory;
- the configured ChatGPT Project supplies Web context; PowerPack does not duplicate its conversations in the prompt.

## GitHub capability

Specify PowerPack first discovers the GitHub plugin/connector through the account-scoped ChatGPT backend and requires enabled/authorized/available state. It then passes the resolved connector to the ChatGPT Web conversation payload as a dynamic `plugin:connector_*` system hint and `@Github` ecosystem mention.

The PR-reading model must invoke the selected GitHub connector through the ChatGPT Web SSE flow. Specify PowerPack parses assistant/tool messages, detects the JIT permission gate and submits the corresponding read-only `allow` continuation with fresh Sentinel tokens. Command execution and web-search fallbacks are forbidden for GitHub evidence.

Connector/plugin IDs are operational identifiers and are redacted from normal reports.

## Immutable Master Prompt + Review Packet PR review

### Phase 1 — manifest

A read-only ChatGPT Web turn resolves exactly one explicit PR and returns:

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

A second read-only ChatGPT Web turn receives:

- immutable snapshot;
- bound ChatGPT Project identity;
- active SPEC context;
- Deep Review Protocol;
- optional previous review;
- user instruction.

It must inspect the exact PR through GitHub tools and return schema 2.0 JSON only.

Specify PowerPack verifies snapshot identity, exact changed-file coverage, Project binding and the installed review-protocol validator.

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
