# Homologation devcontainer

A reproducible environment for running the **T025 `implement-review` homologation**
(`specs/001-single-skill-baseline/T025-validation-runbook.md`) — the live browserless
Codex → ChatGPT Project → GitHub round-trip that a mocked test suite cannot cover.

## What it provides

- Python 3.11, the package installed editable with `[dev]` extras, `pytest`
- the real Spec Kit CLI (`specify`, pinned to `v1.0.4`)
- `gh`, Node LTS
- the Codex CLI, **via a bind mount of your host `~/.codex`** (the standalone binary lives
  there); `postcreate.sh` symlinks it onto `PATH`

## Credential mounts (opt-in)

`devcontainer.json` bind-mounts three host directories read-write:

| Host | Container | Purpose |
|---|---|---|
| `~/.codex` | `/home/vscode/.codex` | `codex login` token + the standalone `codex` binary |
| `~/.claude` | `/home/vscode/.claude` | Claude Code config (executor detection, settings) |
| `~/.config/gh` | `/home/vscode/.config/gh` | `gh` auth for PR resolution |

`initializeCommand` creates these directories on the host first, so the mounts **never fail
to start** — if you have not logged in, they are simply empty and the homologation stops at
the readiness check with an attributable `FAIL` (never a crash). Nothing credential-bearing
is copied into an image layer; the mounts are live references to your host files.

If you would rather not mount real credentials, delete the `mounts` block and run
`codex login` / `gh auth login` inside the container instead.

## Running a homologation

```bash
# once, to find your Project id
specify-powerpack review project discover

# the T025 round-trip for this repo's PR #15
bash .devcontainer/homologate.sh 15 --project speckit-powerpack
```

`homologate.sh`:

1. resolves the PR head SHA (`gh`) and adds a throwaway `git worktree` at it;
2. points that worktree's `origin` at the canonical repo name (the GitHub connector rejects
   a stale post-rename name);
3. `specify-powerpack install` + `review setup` into the worktree;
4. runs `collect-t025-offline-evidence.sh` (runbook §3) then S1 / S6 / S7;
5. writes everything to `specs/001-single-skill-baseline/T025-evidence/` and prints the
   deep-review verdict;
6. removes the worktree on exit.

Default `--timeout` is `3300` s — an `xhigh` deep review of a large SPEC delta does not fit
the CLI's 600 s default.

## Using it for another repository

`homologate.sh` is specific to this repo (the `specs/001-single-skill-baseline` path). For a
different project, run the same steps from that project's checkout — `specify-powerpack
review run` derives the repository from `origin` and needs its own `review setup` Project
binding.
