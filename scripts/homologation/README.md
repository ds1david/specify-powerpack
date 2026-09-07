# PowerPack homologation harness

This harness automates repeatable functional homologation of SpecKit PowerPack across projects while preserving evidence for each run.

The implementation is Python-first so the same orchestration can be used on WSL/Linux and Windows. The current first-class validation target is **WSL/Linux**. Windows uses the same Python harness through `homologate.ps1`.

## Harness self-tests

Do not require `pytest` to be installed globally. Run the harness tests through `uv`:

```bash
cd /home/david/workspace/speckit-powerpack
uv run --extra dev python -m pytest -q \
  tests/test_homologation_harness.py \
  tests/test_review_context_contract.py
```

## WSL baseline

Expected local PowerPack clone:

```text
/home/david/workspace/speckit-powerpack
```

Formal baseline homologation installs:

```text
feat/chatgpt-project-provider-no-browser
```

The target project is explicit or defaults to the current working directory.

## Clean configuration invariant

Every PowerPack-managed homologation scenario must start from managed configuration overwritten by the currently installed candidate package. H1/H2 execute the equivalent of:

```bash
speckit-powerpack update <project> \
  --project-only \
  --force \
  --yes \
  --reset-config \
  --integration codex \
  --bootstrap-speckit
```

Only after that reset does the scenario apply its own review setup/binding. The harness validates that stale ChatGPT Project identifiers/authorization did not survive the reset. A reset failure or stale binding is a scenario `FAIL` and execution stops.

## Scenarios

| Scenario | Executor | Review path | ChatGPT Project | Current harness state |
|---|---|---|---|---|
| H1 | Codex | local Codex smoke | disabled | automated |
| H2 | Codex | Codex + Project-context smoke | enabled | automated + human mission confirmation |
| H3 | Copilot | Codex | disabled | BLOCKED until mixed-provider PowerPack integration exists |
| H4 | Copilot | Codex + Project context | enabled | BLOCKED until mixed-provider PowerPack integration exists |
| H5 | Copilot | two separate local Copilot reviews | unavailable/not used | automated isolated Copilot reviewer smoke |

A `BLOCKED` scenario is not a successful homologation and is intentionally different from `FAIL`.

## H1 on WSL

```bash
cd /home/david/workspace/speckit-powerpack
git fetch
git switch feat/homologation-harness
git pull

sh scripts/homologation/homologate.sh H1 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab
```

H1 captures environment/repository evidence, installs the browserless baseline, overwrites managed config, configures `--no-project`, runs `doctor`, validates `review.json`, executes the Codex smoke and requires the division-by-zero finding plus `POWERPACK_SMOKE_CLI_OK`. It then executes a Web smoke that **must fail closed** because no Project is bound.

## H2 on WSL

H2 is the automated provider-context homologation. For unattended execution it can still receive a Project id, URL or unique name through `--chatgpt-project` or `POWERPACK_CHATGPT_PROJECT`.

For human-driven work, however, **do not manually discover/copy the Project id**. The preferred PowerPack workflow is the interactive browserless selector described below: `review setup --path ...` discovers the Projects visible to the authenticated ChatGPT account, prints a numbered list and asks the user to select the intended Project.

The H2 bind remains a first-class fail-fast gate: bind failure or invalid persisted state stops execution before strict doctor and smoke tests.

## Preferred interactive ChatGPT Project binding

The normal human workflow must let the PowerPack CLI discover and present the available ChatGPT Projects. Do not require an environment variable, Project id, URL or copied Project name.

From the target repository, run:

```bash
cd /home/david/workspace/autonomous-trading-strategy-evolution-lab

speckit-powerpack review setup --path .
```

Expected interaction:

```text
Codex/ChatGPT authorization validated via ~/.codex/auth.json.
Deseja vincular este repositório local a um ChatGPT Project existente? [y/N]: s
 1. <Project name> | <project-id> | <project-url>
 2. <Project name> | <project-id> | <project-url>
 ...
Select Project number: <number>
Repository linked to ChatGPT Project '<Project name>' (...) using ChatGPTProjectProvider.
```

The selector is browserless: Project discovery uses the authenticated ChatGPT account backed by Codex auth and does not launch Playwright or Chromium.

If the user declines the Project prompt, PowerPack configures local Codex review instead. If discovery returns no Projects or the selected index is invalid, binding fails and review must stop.

For automation/non-interactive execution only, explicit selectors remain available:

```bash
speckit-powerpack review setup \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --yes-project \
  --project 'g-p-XXXXXXXX'
```

or `--index N` after a previously inspected discovery list.

## Manual Web review: interactive bind first, then review an explicit PR

A real Web code review is separate from the H2 provider-context smoke. Before `review run --provider web`, bind the target repository to the intended ChatGPT Project with the PowerPack itself.

### 1. Install the candidate CLI you intend to exercise

For local development of the current harness/candidate branch:

```bash
uv tool install --force \
  /home/david/workspace/speckit-powerpack
```

Confirm that the Web PR contract is present:

```bash
speckit-powerpack review run --help
```

The help must advertise both:

```text
--pr PR
--github-plugin-authorized
```

### 2. Let PowerPack discover and bind the ChatGPT Project

```bash
cd /home/david/workspace/autonomous-trading-strategy-evolution-lab
speckit-powerpack review setup --path .
```

Answer `s`/`y` when asked whether to bind a ChatGPT Project. PowerPack then lists the Projects visible to the authenticated account and asks for the Project number. This interactive selection is the preferred human workflow.

A bind failure is a hard stop: do not continue to `doctor` or `review run`.

### 3. Validate the persisted binding and provider readiness

```bash
speckit-powerpack doctor \
  --strict-review \
  /home/david/workspace/autonomous-trading-strategy-evolution-lab
```

The strict doctor must succeed before the review begins. The effective repository configuration should resolve to `provider=chatgpt-project`, Project enabled/required, backend API mode, and a non-empty bound Project identity.

### 4. Confirm GitHub permission in ChatGPT

For Web PR review, grant the ChatGPT/GitHub plugin or connector access to the target GitHub repository. PowerPack cannot grant this permission on the user's behalf; `--github-plugin-authorized` is the user's attestation that the permission was granted.

If the ChatGPT/GitHub integration cannot access the exact PR, the review must fail closed as `BLOCKED_CONFIGURATION`; Project memory or a PR description alone is not proof of PR inspection.

### 5. Run the Web review against an explicit PR

Example for `autonomous-trading-strategy-evolution-lab` PR #92:

```bash
speckit-powerpack review run \
  --provider web \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --pr 92 \
  --github-plugin-authorized \
  --prompt-file /tmp/atsel-033-soak-002-review.md
```

For Web mode, `--pr` is mandatory and is part of the authoritative review identity. The PR must belong to the repository configured as `origin`; a PR URL from another repository is rejected.

The preferred human Web review sequence is:

```text
install candidate CLI
  -> speckit-powerpack review setup
  -> PowerPack discovers Projects
  -> user selects Project number
  -> PowerPack persists binding
  -> doctor --strict-review
  -> confirm ChatGPT/GitHub permission
  -> review run --provider web --pr ...
```

A provider/context smoke passing does **not** by itself mean a Web PR review is homologated. The real PR review must preserve its own PR/base/head/prompt/response evidence.

## Local review contract

Local review intentionally does not require a PR. It resolves the current Git branch to exactly one Spec Kit SPEC and reviews that branch/SPEC pair using the local repository as evidence.

```bash
speckit-powerpack review run \
  --provider codex \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --prompt-file /tmp/local-review.md
```

Passing `--pr` or `--github-plugin-authorized` to a local Codex review is invalid. If the current branch cannot be tied to exactly one SPEC, the local review fails closed instead of reviewing the repository generically.

## H5 Copilot-only on WSL

H5 requires only Git, Spec Kit and an authenticated/ready `copilot` CLI. It does not configure or invoke Codex and does not bind/use ChatGPT Project.

```bash
sh scripts/homologation/homologate.sh H5 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab
```

The harness resolves the current Git branch to exactly one current Spec Kit `spec.md` and launches **two separate** programmatic Copilot CLI sessions. Both reviews use the current branch + SPEC and do not require a PR.

- review 1: correctness, SPEC compliance, regressions, tests and security;
- review 2: fresh adversarial review of concurrency, failure paths, boundaries, idempotency, composition root and vacuously-green tests.

The CLI is started with programmatic prompt/output options and a read-only permission policy: file reads and selected Git inspection commands are allowed; write, memory and URL tools plus mutating Git commands are denied. The harness requires a distinct marker from each review and verifies that both HEAD and working-tree state are unchanged afterward.

H5 is currently an **isolated Copilot reviewer capability smoke**. It does not claim that the packaged PowerPack yet has a fully materialized `--integration copilot` contract; H3/H4 remain blocked until that provider abstraction exists.

## Installation source

Formal baseline, default:

```bash
--install-source remote \
--powerpack-ref feat/chatgpt-project-provider-no-browser
```

Local development checkout:

```bash
--install-source local \
--powerpack-repo /home/david/workspace/speckit-powerpack
```

## Evidence

Each run creates:

```text
~/powerpack-homologation/YYYYMMDD-HHMMSS/
```

H1/H2 include `powerpack-config-reset.txt` plus scenario-specific setup/bind/doctor/smoke evidence. H2 additionally preserves `project-bind.txt`. H5 preserves branch/SPEC resolution, two independent Copilot review outputs and before/after Git state.

The harness never copies `~/.codex/auth.json` or Copilot credentials into evidence.

## Dirty repositories

A dirty target repository is captured as evidence and reported as `WARN` by default. For a strict clean-start run:

```bash
sh scripts/homologation/homologate.sh H1 --require-clean
```

## Skip reinstalling the tool

During local iteration only:

```bash
sh scripts/homologation/homologate.sh H1 --skip-tool-install
```

Do not use this option for a formal baseline unless the installed source/version has been independently captured.

## Windows wrapper

The same Python harness is available through:

```powershell
.\scripts\homologation\homologate.ps1 H1 --project-path C:\workspace\target-project
```

WSL is the current release-homologation focus.
