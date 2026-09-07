# PowerPack homologation harness

This harness automates repeatable functional homologation of SpecKit PowerPack across projects while preserving evidence for each run.

The implementation is Python-first so the same orchestration can be used on WSL/Linux and Windows. The current first-class validation target is **WSL/Linux**. Windows uses the same Python harness through `homologate.ps1`.

## Harness self-tests

Do not require `pytest` to be installed globally. Run the harness tests through `uv`:

```bash
cd /home/david/workspace/speckit-powerpack
uv run --extra dev python -m pytest -q tests/test_homologation_harness.py
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

Provide a ChatGPT Project id, URL or unique name:

```bash
export POWERPACK_CHATGPT_PROJECT='g-p-XXXXXXXX'

sh scripts/homologation/homologate.sh H2 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab
```

Or:

```bash
sh scripts/homologation/homologate.sh H2 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --chatgpt-project 'g-p-XXXXXXXX'
```

H2 first overwrites old managed configuration and then performs an explicit Project bind using `review setup --yes-project --project ...`.

The bind is a first-class fail-fast gate:

1. execute the bind and save stdout/stderr in `project-bind.txt`;
2. require exit code zero;
3. reload `review.json`;
4. require `provider=chatgpt-project`, `required=true`, `enabled=true`, `mode=backend-api`, `project_id` and `project_url`;
5. only then run strict doctor and smoke tests.

Any bind command failure or invalid persisted state ends H2 immediately as `FAIL`; no doctor or smoke runs afterward.

After a valid bind, H2 requires non-empty Project response, expected Project name, `1 + 1 = 2`, and at most 100 words. The harness then asks for human confirmation that the returned mission matches the intended Project. In `--non-interactive` mode this semantic step remains `BLOCKED` rather than being fabricated as verified.

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
