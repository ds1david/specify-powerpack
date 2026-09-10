# Homologation devcontainer

A reproducible environment for running the **T025 `implement-review` homologation**
(`specs/001-single-skill-baseline/T025-validation-runbook.md`) — the live browserless
Codex → ChatGPT Project → GitHub round-trip that a mocked test suite cannot cover.

## Architecture — what actually runs the review

The review is **not** run by chatgpt.com. It is run by the **Codex CLI**, locally:

```
  your machine (host, or this devcontainer)
    homologate.sh
      └─ specify-powerpack review run
           └─ codex exec  ── the REVIEWER: model gpt-5.6-sol, effort xhigh,
              │               --sandbox read-only, no shell, no web search
              │
              ├─ MCP: codex_apps  ──►  OpenAI backend  ──►  GitHub Codex App (your OAuth grant)  ──►  api.github.com
              │        github.fetch_pr_patch / fetch_file / compare_commits …
              │        (the HTTP to GitHub runs on OpenAI's servers, not from your box)
              │
              └─ ChatGPT Project "specify-powerpack"  ──  ~2 serialised conversations,
                 pasted into the prompt as read-only *background memory* only.
                 The Project does not review anything; it is a folder of chats.
```

What each piece contributes:

| Piece | Runs where | Role |
|---|---|---|
| `codex exec` | your host / this container | **the reviewer** — reads the PR, applies the deep-review protocol, emits `review.json` |
| GitHub Codex App (`codex_apps` MCP) | OpenAI infra + GitHub | fetches the PR code at the pinned head SHA; holds the GitHub OAuth token |
| ChatGPT Project | — (serialised into the prompt) | background memory (prior design conversations); SPEC + PR evidence always win |
| your `~/.codex/auth.json` | your box | authenticates `codex exec` to OpenAI — that is the *only* token your box holds |

"**Browserless**" means no Chrome / Playwright / CDP driving a web UI — it is all API + MCP.

### Why `fetch_file` and not a `git clone`

The reviewer never clones. Every code read goes through the GitHub App, one file at a time
(hence the hundreds of `fetch_file` calls on a large PR). That is deliberate:

- **Integrity.** The review must bind to the PR *as GitHub sees it* at the exact head SHA
  (the immutable snapshot; the gate also checks `local HEAD == PR head SHA`). A local clone
  could be stale, on the wrong ref, dirty, or tampered with. Fetching each file at the
  pinned SHA guarantees the reviewer saw exactly what is on the PR.
- **Sandbox.** `codex exec` runs `--sandbox read-only` and is told not to run shell commands
  or web search. It has no working tree of its own to clone into, and cannot be tricked into
  running a malicious repo's build scripts or reading secrets off your disk.
- **Attestation.** Every `coverage.inspection_evidence` entry in `review.json` is traceable
  to a specific GitHub App tool call. `require_github_tool_evidence` rejects the review if it
  fell back to a shell or web search. A clone would make "what did it actually look at?"
  unprovable.
- **Auth reuse.** You authorised the GitHub Codex App in ChatGPT once (OAuth). The reviewer
  reuses that grant; no deploy keys, and the GitHub token never touches your machine.

The cost is round-trips (each fetch is a hop through the connector). The design trades that
for verifiability.

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

### Lifecycle — what runs when

The container is created the moment you choose *Reopen in Container* (or run
`devcontainer up`). Order:

| Step | Where | When | This repo |
|---|---|---|---|
| `initializeCommand` | **host** | before the container exists | `mkdir -p ~/.codex ~/.claude ~/.config/gh` (so the bind mounts cannot fail) |
| image acquire | — | first time, then cached | pull `mcr…/python:3.11` + compose the `github-cli` / `node` features |
| container create | — | on create / rebuild | apply mounts, env, bind the workspace folder |
| `postCreateCommand` | container | **once**, on create / rebuild | `bash .devcontainer/postcreate.sh` — `pip install -e .[dev]`, Spec Kit `v1.0.4`, symlink `codex` (~1–2 min) |
| container start + attach | container | every start / every VS Code window | — |

So a plain window reload does **not** re-run `postcreate.sh`; only editing
`devcontainer.json` (VS Code then offers *Rebuild Container*) or *Dev Containers: Rebuild*
does. The container you see in Docker Desktop stays up while VS Code is attached (and
usually after you close the window, until you *Reopen Folder Locally* or stop it there).

`homologate.sh` is **not** a lifecycle hook — run it by hand in the container terminal once
`postcreate.sh` has finished. First sanity check in that terminal:

```bash
specify-powerpack --version      # this checkout
specify --version                # Spec Kit v1.0.4
codex --version                  # from the mounted ~/.codex; if MISSING, your host codex
                                 # is not the standalone build — `npm i -g @openai/codex`
gh auth status                   # from the mounted ~/.config/gh
```

## Following the run in real time

`homologate.sh` prints everything to the terminal it runs in (timestamped step banners). The
deep review prints a rolled-up status line about every 30 s —
`working… 214 GitHub calls (fetch_file×198, fetch_file_lines×9, …) · 7.3 min` — plus
one-off milestones (`codex turn started`, `drafting the review verdict…`, `✓ turn
completed`). It also `tee`s the S6 review to a file, so from a second terminal / pane:

```bash
tail -f specs/001-single-skill-baseline/T025-evidence/S6-review-run.txt
```

For the whole script in a file too: `bash .devcontainer/homologate.sh 15 --project g-p-… 2>&1 | tee /tmp/homologate.log`.
The deep review can run 10–40 min — launch it under `tmux` / `screen` (or
`nohup … &`) so a disconnect does not kill it.

### How many GitHub calls to expect

There is **no fixed number** — the reviewer is an autonomous agent and decides how to
inspect each file (whole file vs. line ranges, which related callers/tests to pull, whether
to re-read). It scales with the PR:

- snapshot turn: ~3 calls (`list_pr_changed_filenames`, `get_pr_info`, `compare_commits`)
- review turn: one or more per **inspected** file. PR #15 changed 57 files and the round-1
  review inspected **89** (57 changed + 32 related), so a few hundred calls total is normal.

The review turn runs `codex exec --ignore-user-config`, so your `~/.codex` MCP servers,
hooks and plugins are **not** loaded — a context-mode / indexer hook firing on every tool
call would otherwise dominate the runtime (and pollute the count). If the status line shows
`+N other` calls, something is still leaking in.

The only hard limit is `--timeout` (wall clock). The finished
`review.json` records `coverage.inspected_files`; the CLI result JSON prints
`"github_calls": <n>` and `homologate.sh` echoes it after the verdict, so after one clean
run you have your own baseline.

### Token cost — the `--effort` lever

Each fetched file is read into the reviewer model's context and reasoned over at the chosen
effort, then the protocol makes it emit per-file `inspection_evidence`, a requirement matrix
and a `verdict_challenge`. That is where your Codex/ChatGPT tokens go — a 57-file PR at
`xhigh` is a large review (tens of thousands of tokens, sometimes more).

`xhigh` is the SPEC's reviewer contract (`model-routing.json` → `reviewer_contract`), but a
homologation run is a *validation* of the flow, not the canonical gate — a lower effort
still produces a schema-valid verdict for far fewer tokens:

```bash
bash .devcontainer/homologate.sh 15 --project g-p-… --effort high     # ~half the tokens of xhigh
bash .devcontainer/homologate.sh 15 --project g-p-… --effort medium   # cheaper still
```

Other levers: `--model <cheaper>` (changes review quality); the PR size itself (57 files
here because SPEC-001 is a whole cleanup — nothing to do now). `--timeout` only caps wall
time, not tokens.

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
of what is available. `homologate.sh` streams a rolled-up deep-review status line every
~30 s (see *Following the run*); add `--quiet` to `specify-powerpack review run` to silence
it.

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
