# Installation

This is the canonical first-install guide for **Specify PowerPack**. It assumes the user has never used PowerPack before.

Specify PowerPack extends the official GitHub Spec Kit; it does not replace it. The bootstrap can install a tested Spec Kit release when needed.

The canonical repository is `ds1david/specify-powerpack`. The canonical CLI is `specify-powerpack`. The previous `speckit-powerpack` command remains available as a compatibility alias during migration.

## What you need

Required on Linux, WSL, macOS or Windows:

- Python 3.11+
- Git
- network access to GitHub for installation/update

For the browserless code-review provider you also need:

- Codex CLI available on `PATH`
- `codex login` completed for the ChatGPT account that owns or can access the desired ChatGPT Project
- the GitHub App/connector installed and OAuth-authorized for that ChatGPT account, with access to the repository being reviewed

You do **not** need Chrome, Chromium, Playwright, CDP or ChatGPT-Web2API.

## Fastest installation

Clone the Specify PowerPack repository, then run the wrapper for your operating system.

Linux / WSL / macOS:

```bash
./install.sh --project /path/to/your-project --integration codex
```

Windows PowerShell:

```powershell
.\install.ps1 --project C:\path\to\your-project --integration codex
```

Direct Python is equivalent and is the portable fallback:

```bash
python install.py --project /path/to/your-project --integration codex
```

The bootstrap installs `uv` when necessary, installs the `specify-powerpack` CLI, then invokes the same PowerPack initialization contract used by the CLI.

## Installing a branch or pinned revision

For development/homologation:

```bash
python install.py \
  --repository https://github.com/ds1david/specify-powerpack.git \
  --ref feat/browserless-codereview-stable \
  --project /path/to/project \
  --integration codex
```

For reproducible installation, prefer an immutable commit SHA in `--ref`.

## First install into a project

If the project has never used Spec Kit or Specify PowerPack:

```bash
specify-powerpack init /path/to/project --integration codex
```

`init`:

1. verifies/bootstraps official Spec Kit;
2. initializes Spec Kit when `.specify/` does not exist;
3. materializes PowerPack runtime/configuration under `.specify/powerpack/`;
4. installs the Specify PowerPack Spec Kit extension and preset.

It does not authenticate ChatGPT and does not guess a ChatGPT Project.

If the repository is already a Spec Kit project, use:

```bash
specify-powerpack install . --integration codex --bootstrap-speckit
```

## Configure the browserless reviewer

Authenticate Codex first:

```bash
codex login
```

Optionally inspect Projects visible to that account:

```bash
specify-powerpack review project discover
```

Bind the repository interactively:

```bash
specify-powerpack review setup --path .
```

Or non-interactively:

```bash
specify-powerpack review setup --path . --project '<project-id-or-unique-name-or-url>'
```

`review setup` validates the Codex-authenticated ChatGPT backend, resolves a ChatGPT Project and verifies the GitHub App/connector state. The persisted project binding uses `authorization = codex-backend-api` and `context_mode = serialized`.

## Verify readiness

Installation-only checks:

```bash
specify-powerpack doctor .
```

Live review checks, including GitHub connector discovery:

```bash
specify-powerpack doctor . --strict-review
```

Detailed state:

```bash
specify-powerpack review status --path . --live
```

A strict review-ready installation must prove Codex CLI, Codex auth, ChatGPT Project binding and a live GitHub App/connector.

## Run a code review

The PR is always explicit:

```bash
specify-powerpack review run \
  --path . \
  --pr 123 \
  --prompt 'Perform the complete Deep Review Evidence Protocol.'
```

A canonical GitHub PR URL is also accepted.

Second and later rounds can validate all previous findings:

```bash
specify-powerpack review run \
  --path . \
  --pr 123 \
  --previous .specify/powerpack/reviews/<previous>.json
```

The review fails closed if the local HEAD differs from the PR head, the branch cannot resolve exactly one Spec Kit SPEC, GitHub tool evidence is missing, Project context evidence is missing, or schema 2.0 validation fails.

## Update

Check the installed source:

```bash
specify-powerpack update . --check
```

Update the CLI and refresh managed project assets:

```bash
specify-powerpack update .
```

Refresh only project assets:

```bash
specify-powerpack update . --project-only
```

Reset mutable PowerPack configuration only when intentionally discarding local customization/binding:

```bash
specify-powerpack update . --project-only --reset-config
```

See `UPDATES.md` before using reset.

## Compatibility alias

Existing environments that still invoke `speckit-powerpack` continue to work. New documentation and automation should use `specify-powerpack`.

The Python import package remains `speckit_powerpack` for compatibility with existing integrations; that module name is an implementation identifier, not the product name.

## What is stored in the repository

`.specify/powerpack/` contains versionable policy/configuration, generated runtime scripts and review outputs. Raw Codex/ChatGPT tokens are never copied into the repository.

Authentication remains in the user's Codex authentication store (`~/.codex/auth.json` or the platform-equivalent home path used by Codex).

## Troubleshooting

`Codex authentication file not found` → run `codex login`.

`No ChatGPT Projects were discovered` → confirm the Codex-authenticated account can access a ChatGPT Project.

`GitHub App is not ready` → install/connect GitHub in ChatGPT/Codex and grant repository access.

`local HEAD does not match PR head` → check out/update the exact PR head before reviewing.

`Could not resolve exactly one Spec Kit SPEC` → align the current branch with a single `specs/<spec>/spec.md`.
