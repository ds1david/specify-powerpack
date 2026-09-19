# Codex-first installation

For a new user, start with [`INSTALLATION.md`](INSTALLATION.md). This page records the Codex-specific path for **Specify PowerPack**.

## Prerequisites

- Python 3.11+
- Git
- Codex CLI
- a ChatGPT account authenticated through `codex login`
- GitHub App/connector connected to the same ChatGPT account for PR review

No browser automation dependency is part of the supported path.

## Install

From a Specify PowerPack clone:

```bash
./install.sh --project /path/to/project --integration codex
```

or:

```bash
python install.py --project /path/to/project --integration codex
```

On Windows:

```powershell
.\install.ps1 --project C:\path\to\project --integration codex
```

The equivalent installed-CLI command is:

```bash
specify-powerpack init /path/to/project --integration codex
```

## Authenticate and bind the Project

```bash
codex login
cd /path/to/project
specify-powerpack review project discover
specify-powerpack review setup --path .
specify-powerpack doctor . --strict-review
```

The repository binding stores only Project identity/policy. OAuth bearer material stays in the user Codex authentication store.

## Model roles

The packaged default Codex routing remains:

| Role | Model | Effort | Authority |
|---|---|---:|---|
| orchestrator / implementation | `gpt-5.6-terra` | high | writes and phase ownership |
| bounded economical work | `gpt-5.6-luna` | medium | narrow mechanical work |
| semantic gate | `gpt-5.6-sol` | high | read-only semantic checks |
| deep reviewer | `gpt-5.6-sol` | xhigh | read-only review |

The browserless PR reviewer is an external `codex exec --ephemeral --sandbox read-only` turn because it must materialize the configured Codex App/MCP tool surface. The workflow must not recursively spawn reviewer CLIs without an explicit provider contract.

## First review

```bash
specify-powerpack review run --path . --pr <number>
```

Review output is written beneath `.specify/powerpack/reviews/` unless `--output` is supplied.

The old `speckit-powerpack` executable is a migration alias only; new instructions should use `specify-powerpack`.

For architecture and review invariants see [`PROCESS_ARCHITECTURE.md`](PROCESS_ARCHITECTURE.md) and [`IMPLEMENT_REVIEW.md`](IMPLEMENT_REVIEW.md).
