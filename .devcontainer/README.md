# Homologation devcontainer

A reproducible environment for running the **T025 `implement-review` homologation**
(`specs/001-single-skill-baseline/T025-validation-runbook.md`) — the live browserless
Codex → ChatGPT Project → GitHub round-trip that a mocked test suite cannot cover.

## Opening the container

**VS Code** (needs the *Dev Containers* extension `ms-vscode-remote.remote-containers` and a
running Docker):

```bash
code .            # from the repo root, inside WSL
```

Then accept the "Reopen in Container" prompt, or `Ctrl+Shift+P` →
`Dev Containers: Reopen in Container`. Build + `postCreate` output: the
`Starting Dev Container (show log)` link in the notification, or `Ctrl+Shift+P` →
`Dev Containers: Show Container Log`. When it finishes, open a terminal (`` Ctrl+` ``) — it
is *inside* the container.

**Headless** (no VS Code):

```bash
npm i -g @devcontainers/cli
devcontainer up   --workspace-folder .          # prints build + postCreate logs
devcontainer exec --workspace-folder . bash .devcontainer/homologate.sh 15 --project g-p-…
```

You do **not** have to use the container — `homologate.sh` runs this checkout's code
directly (`python3 -m speckit_powerpack`), so running it on the host works too, as long as
`codex login` / `gh auth login` are done there.

## Following the run in real time

`homologate.sh` prints everything to the terminal it runs in (timestamped step banners; the
deep review streams each GitHub tool call and a heartbeat every ~25 s). It also `tee`s the
S6 review to a file, so from a second terminal / pane:

```bash
tail -f specs/001-single-skill-baseline/T025-evidence/S6-review-run.txt
```

For the whole script in a file too: `bash .devcontainer/homologate.sh 15 --project g-p-… 2>&1 | tee /tmp/homologate.log`.
The deep review can run 10–40 min — launch it under `tmux` / `screen` (or
`nohup … &`) so a disconnect does not kill it.

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
# once, to find your Project id (copy the g-p-… value, not the name)
specify-powerpack review project discover

# the T025 round-trip for this repo's PR #15
bash .devcontainer/homologate.sh 15 --project g-p-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

`--project` takes the **Project id** (`g-p-…`) or its full
`https://chatgpt.com/g/g-p-…/project` URL. A bare display name works only if it is an
*exact, unique* match — a renamed Project or a partial name will be rejected with the list
of what is available. `homologate.sh` streams the deep-review progress (each GitHub tool
call, a heartbeat every ~25 s) so you can see it is alive; add `--quiet` to
`specify-powerpack review run` to silence it.

`homologate.sh` always runs **this checkout's** code (via `PYTHONPATH`), never a
globally-installed `specify-powerpack`, so a stale global install cannot make it
materialise removed-command assets.

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
