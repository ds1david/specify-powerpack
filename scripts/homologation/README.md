# PowerPack homologation harness

This harness automates repeatable functional homologation of SpecKit PowerPack across projects while preserving evidence for each run.

The implementation is Python-first so the same orchestration can be used on WSL/Linux and Windows. The current first-class validation target is **WSL/Linux**. Windows uses the same Python harness through `homologate.ps1` and will receive the same scenario validation after the WSL baseline is approved.

## WSL baseline

Expected local PowerPack clone:

```text
/home/david/workspace/speckit-powerpack
```

This path is only the default for `--install-source local`. Formal baseline homologation installs the known browserless reference directly with `uv`:

```text
feat/chatgpt-project-provider-no-browser
```

The target project is always explicit or defaults to the current working directory. This allows moving between repositories without editing the scripts.

## Scenarios

| Scenario | Executor | Reviewer | ChatGPT Project | Current harness state |
|---|---|---|---|---|
| H1 | Codex | Codex | disabled | automated |
| H2 | Codex | Codex + Project context | enabled | automated + human mission confirmation |
| H3 | Copilot | Codex | disabled | BLOCKED until Copilot integration exists |
| H4 | Copilot | Codex + Project context | enabled | BLOCKED until Copilot integration exists |
| H5 | Copilot | Copilot | unavailable | BLOCKED until isolated Copilot mode exists |

A `BLOCKED` scenario is not treated as a successful homologation and is intentionally different from `FAIL`.

## H1 on WSL

From the PowerPack repository:

```bash
cd /home/david/workspace/speckit-powerpack
git fetch
git switch feat/homologation-harness

sh scripts/homologation/homologate.sh H1 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab
```

The harness will:

1. capture OS, Python executable, Node, uv, Spec Kit, Codex, Copilot and Git versions;
2. capture repository branch, HEAD, remotes and status;
3. install the browserless PowerPack baseline with `uv tool install --force`;
4. materialize the PowerPack with `--integration codex`;
5. configure `--no-project`;
6. run `doctor`;
7. assert `review.json` uses Codex and has Project context disabled;
8. run the positive Codex smoke and require the division-by-zero finding plus `POWERPACK_SMOKE_CLI_OK`;
9. run the Web smoke expecting it to fail because no Project is bound;
10. preserve both positive and negative smoke JSON files and emit a final summary.

The negative Web smoke is a **PASS condition** for H1. If it unexpectedly succeeds, H1 fails.

## H2 on WSL

Provide a ChatGPT Project id, URL or unique name through an environment variable:

```bash
export POWERPACK_CHATGPT_PROJECT='g-p-XXXXXXXX'

sh scripts/homologation/homologate.sh H2 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab
```

Or pass it directly:

```bash
sh scripts/homologation/homologate.sh H2 \
  --project-path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --chatgpt-project 'g-p-XXXXXXXX'
```

H2 requires the automated Project-context checks to pass:

- non-empty response;
- expected Project name present;
- `1 + 1 = 2` answer present;
- response no longer than 100 words.

The harness then prints the returned Project response and asks whether the mission semantically matches the expected Project. H2 is only `PASS` after that human confirmation.

For unattended evidence collection, use `--non-interactive`. In that mode H2 remains `BLOCKED` at the semantic confirmation step instead of pretending the mission was verified.

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

The local mode is useful while developing the harness or a candidate branch. A release/baseline homologation should use an explicit remote Git ref so the tested source is reproducible.

## Evidence

Each run creates a timestamped directory below:

```text
~/powerpack-homologation/YYYYMMDD-HHMMSS/
```

Typical H1 evidence:

```text
common/
  environment.json
  environment.txt
  repository-before.txt
H1/
  powerpack-project-install.txt
  review-setup-no-project.txt
  doctor.txt
  review-config.json
  cli-smoke.txt
  cli-smoke.json
  web-negative-smoke.txt
  web-negative-smoke.json
  repository-after.txt
  result.json
  result.txt
summary.json
```

The harness never copies `~/.codex/auth.json` into evidence.

## Dirty repositories

A dirty target repository is captured as evidence and reported as `WARN` by default. This is intentional because `speckit-powerpack install` can materialize project files and H2 may follow H1 in the same repository.

For a strict clean-start run:

```bash
sh scripts/homologation/homologate.sh H1 --require-clean
```

## Skip reinstalling the tool

During local iteration only:

```bash
sh scripts/homologation/homologate.sh H1 --skip-tool-install
```

Do not use this option for a formal baseline unless the installed PowerPack source/version has been independently captured.

## Windows wrapper

The same harness can be invoked later on Windows with:

```powershell
.\scripts\homologation\homologate.ps1 H1 --project-path C:\workspace\target-project
```

WSL is the current homologation focus; validate the WSL baseline before treating Windows results as release evidence.
