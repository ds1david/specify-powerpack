# Specify PowerPack

> **Status: pre-release / evolving.** This is a personal project in continuous evolution. It is driven by the workflow, quality and safety criteria I consider useful, while being progressively generalized into a reusable PowerPack for projects of different contexts. Changes must distinguish a real defect from a new capability request.

Specify PowerPack is an extension layer for the official [GitHub Spec Kit](https://github.com/github/spec-kit). It does **not** fork or replace Spec Kit. It adds one command — `speckit-implement-review` — a deep, evidence-validated implementation-review gate: convergence, capability-based quality gates, an independent Sol review and a browserless ChatGPT Project + GitHub code-review gate.

The canonical repository is `ds1david/specify-powerpack`. The canonical CLI is `specify-powerpack`; the previous `speckit-powerpack` command is retained as a compatibility alias during migration.

> **Single-command baseline (SPEC-001).** Earlier releases also shipped `speckit-implement`, `speckit-converge`, `speckit-checklist-converge`, `speckit-full-cycle` and a `speckit-debt-*` lifecycle. Those were removed to consolidate the supported surface; `implement-review` now re-uses upstream Spec Kit `speckit-implement` / `speckit-converge` directly. Removed capabilities may return through new specs.

## Workflow

```text
speckit-specify → speckit-clarify → speckit-plan → speckit-tasks → speckit-analyze
→ speckit-implement            (upstream Spec Kit)
→ speckit-implement-review     (Specify PowerPack)
```

`implement-review` owns convergence (via upstream `speckit-converge`), quality gates, independent Sol review and the final Project-aware GitHub review. Findings return to implementation; any implementation change invalidates approvals bound to an earlier snapshot.

## What is implemented

- repository-evidence predecessor enforcement (a completed `tasks.md` plus a real change delta);
- convergence and review repair loops;
- Deep Review Evidence Protocol schema 2.0 + validator;
- capability-based quality gates instead of hard-coded Maven/npm/pytest assumptions;
- Codex/Claude executor routing;
- browserless ChatGPT Project context;
- GitHub App/connector discovery and OAuth readiness checks;
- GitHub tool execution through the official Codex Apps MCP runtime;
- immutable two-phase GitHub PR review;
- cross-platform installer for Linux/WSL/macOS and Windows;
- PowerPack-managed Spec Kit bootstrap/update.

## Browserless review architecture

```text
repository .specify/powerpack/review.json
             │
             ├─ ChatGPT Project id/name
             │
             ▼
       ~/.codex/auth.json
             │
      ChatGPT backend reads
             │
      serialized Project context
             │
             ├───────────────┐
             │               │
             ▼               ▼
       active Spec Kit     GitHub App discovery
       artifacts           + OAuth/availability
             │               │
             └──────┬────────┘
                    ▼
          codex exec --json --ephemeral
          --sandbox read-only
                    │
          [$github](app://connector)
                    │
              codex_apps MCP
                    │
                GitHub tools
                    │
          exact PR/diff/file evidence
                    │
              schema 2.0 review
```

There is no Chrome, CDP, Playwright, Selenium or Web2API in the supported production path.

### What “Project context” means

Specify PowerPack reads the bound ChatGPT Project through account-scoped ChatGPT backend APIs, serializes Project metadata/instructions and recent Project conversations, and injects that material as read-only context for the review turn.

This is deliberately reported as:

```text
project_context_serialized = true
native_project_binding      = false
response_visible_in_project = false
```

The review is **not** written as a native conversation inside the ChatGPT Project.

### What “GitHub connector” means

Specify PowerPack does not manually inject private `tools[]` into `/backend-api/codex/responses`. It discovers the installed GitHub App/connector, then explicitly selects it with:

```text
[$github](app://<connector-id>)
```

The Codex runtime owns App resolution, MCP tools, approvals, tool execution and continuation. Specify PowerPack observes the JSONL lifecycle and requires structural `codex_apps` GitHub tool-call/result evidence. Shell and web-search fallbacks are rejected.

## Immutable code review

`review run` has two phases.

### Phase A — PR manifest

The GitHub App resolves the exact PR, base ref/SHA, merge-base, head SHA and complete changed-file list. Specify PowerPack verifies local `HEAD == PR head SHA`, resolves exactly one active Spec Kit SPEC and computes a deterministic SHA-256 snapshot digest.

### Phase B — deep review

The review receives:

- immutable PR manifest;
- active SPEC artifacts;
- serialized ChatGPT Project context;
- complete Deep Review Protocol 2.0;
- previous review on round 2+;
- exact GitHub App binding.

Specify PowerPack requires GitHub tool evidence, exact changed-file coverage, snapshot identity match and literal Project-context evidence before validating the review JSON.

Trade-off: two phases add latency, but avoid approving an ambiguous or stale snapshot.

## First installation

For someone who has never used Specify PowerPack, start with [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

Minimum prerequisites:

- Python 3.11+
- Git
- internet access to GitHub/ChatGPT
- a ChatGPT account eligible for the Codex CLI / Apps used by your environment

`uv` and official Spec Kit can be bootstrapped by the installer.

### Linux / WSL / macOS

From a clone of this repository:

```bash
./install.sh --project /path/to/project --integration codex
```

Or directly:

```bash
python3 install.py --project /path/to/project --integration codex
```

### Windows PowerShell

```powershell
.\install.ps1 --project C:\path\to\project --integration codex
```

The installer installs the Specify PowerPack CLI with `uv`, then `specify-powerpack init` bootstraps official Spec Kit when required and materializes the PowerPack preset/extension/runtime.

## Review setup

After project installation:

```bash
codex login
cd /path/to/project
specify-powerpack review setup --path .
specify-powerpack doctor . --strict-review
```

`review setup` lists the ChatGPT Projects visible to the Codex-authenticated account, saves the selected Project binding, and verifies the GitHub App/connector state.

The GitHub App must already be installed/connected in the ChatGPT/Codex account and authorized for repositories you intend to review.

## Run a code review

The current local branch must correspond to the exact GitHub PR head and exactly one Spec Kit SPEC.

```bash
specify-powerpack review run \
  --path . \
  --pr 92 \
  --prompt "Perform the complete Deep Review Evidence Protocol."
```

For a subsequent round:

```bash
specify-powerpack review run \
  --path . \
  --pr 92 \
  --previous .specify/powerpack/reviews/<previous>.json
```

A successful transport is not automatically an approval. The final result remains `APPROVED`, `CHANGES_REQUIRED` or `BLOCKED` according to the Deep Review Protocol.

## Diagnostics

```bash
specify-powerpack doctor .
specify-powerpack doctor . --strict-review
specify-powerpack review status --path . --live
specify-powerpack review project discover
```

`--strict-review` performs live Codex/Project/GitHub readiness checks.

## Updates

```bash
specify-powerpack update . --check
specify-powerpack update .
```

Refresh only the project materialization:

```bash
specify-powerpack update . --project-only
```

Configuration reset is explicit:

```bash
specify-powerpack update . --project-only --reset-config
```

## Installed project layout

```text
.specify/
└── powerpack/
    ├── bin/
    │   ├── powerpack.py
    │   ├── capabilities.py
    │   └── review_protocol.py
    ├── model-routing.json
    ├── prerequisites.json
    ├── quality-gates.json
    ├── review.json
    ├── update.json
    ├── deep-review-protocol.md
    └── reviews/            # local generated review artifacts
```

Credentials are **not** stored in the repository. Codex authentication remains in `~/.codex/auth.json`.

## Design principles

```text
DISCOVER CAPABILITY
        ↓
SELECT STRATEGY
        ↓
EXECUTE CONTRACT
```

Specify PowerPack is intended to remain language/framework/build-tool agnostic. Project-specific customizations belong in configuration/policy/domain material rather than forks of generated workflow skills.

## Documentation

- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) — first contact, installation and repository setup.
- [`docs/PROCESS_ARCHITECTURE.md`](docs/PROCESS_ARCHITECTURE.md) — real runtime architecture and boundaries.
- [`docs/IMPLEMENT_REVIEW.md`](docs/IMPLEMENT_REVIEW.md) — immutable review protocol and repair loop.
- [`docs/FULL_CYCLE.md`](docs/FULL_CYCLE.md) — full-cycle orchestration.
- [`docs/CUSTOMIZATION.md`](docs/CUSTOMIZATION.md) — supported customization boundaries.
- [`docs/PORTABILITY.md`](docs/PORTABILITY.md) — capability-driven portability.
- [`docs/TECHNICAL_DEBT.md`](docs/TECHNICAL_DEBT.md) — debt governance.
- [`docs/UPDATES.md`](docs/UPDATES.md) — update/recovery behavior.
- [`docs/DECISIONS_AND_TRADEOFFS.md`](docs/DECISIONS_AND_TRADEOFFS.md) — architecture decisions and trade-offs.

## Safety boundaries

- GitHub review is read-only.
- Shell/web-search fallback is rejected for GitHub review evidence.
- Project context is background memory; SPEC + immutable PR evidence are authoritative on conflict.
- No raw OAuth/access tokens are printed or stored in repository config.
- Findings cannot be converted into debt merely to force convergence.
- Specify PowerPack workflows do not authorize merge, GitHub approval, ready-for-review, force-push or destructive reset.
