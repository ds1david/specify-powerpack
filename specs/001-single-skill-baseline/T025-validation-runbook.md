# T025 — Validation Runbook: full `implement-review` flow on the single-skill baseline

**Task:** `tasks.md` **T025** (US2 / SC-003), tracked as **T051** while open. Prove the
complete `speckit-implement-review` flow runs end to end after the SPEC-001 cleanup, and
that **no step fails because of a removed command or a removed runtime helper**.

**Who runs this:** a person with live Codex + GitHub access. The live half (S1, S3, S6, S7)
cannot run in CI or an offline sandbox; the offline half is automated (see §3).

**Deliverable to close the task:** a committed
`specs/001-single-skill-baseline/T025-evidence/` directory (evidence files + a filled
`RESULT.md`), the [§8 checklist](#8-completion-checklist) all ticked, and `tasks.md` T025 +
T051 flipped to `[X]` with a pointer to `T025-evidence/RESULT.md`.

---

## 1. What "pass" means

SC-003 is about **attribution**, not the review verdict. `CHANGES_REQUIRED`, `BLOCKED`, or
`BLOCKED_CONFIGURATION` caused by a genuinely missing Codex/Project/GitHub credential is an
**acceptable** outcome — record it as `BLOCKED (environmental)` and, if you cannot obtain
the credential, that is the honest terminal state of T025 (see §5).

The task **FAILS** only if any step dies with:

- `ModuleNotFoundError` / `ImportError` / `AttributeError` / `NameError` /
  `No such file or directory` naming `debt.py`, `full_cycle.py`, `powerpack_debt`,
  `powerpack_full_cycle`, `implement_runs`, `latest_implement_files`,
  `technical-debt*.json`, `full-cycle.json`;
- "unknown command" / "not found" for a **PowerPack** `speckit.implement` /
  `speckit.converge` / `speckit.checklist-converge` / `speckit.full-cycle` /
  `speckit.debt-*` (the hyphenated upstream `speckit-implement` / `speckit-converge` are
  expected and correct);
- a `prereq check` that consults an `implement` **state receipt** instead of the
  `implementation-evidence` check;
- the capability quality gate returning `NOT_APPLICABLE` for a change set that is clearly
  not documentation-only (the Phase-8 regression — must already be fixed on the branch
  under test).

**Capture the exact stdout, stderr and exit code of every command.** That is the evidence.

---

## 2. Prerequisites

### 2.0 Install this branch into another repository

The branch under test is `feat/spec-001-single-skill-baseline` on
`https://github.com/ds1david/specify-powerpack.git`. Pick **one** install path — all
produce the same state (`.specify/powerpack/bin/` = only `powerpack.py`,
`capabilities.py`, `review_protocol.py`; `powerpack-core` = `{speckit.implement-review}`).

Set targets first:

```bash
export PP=/abs/path/to/the/OTHER/repo        # a git repo you want to review with implement-review
export PPBRANCH=feat/spec-001-single-skill-baseline
```

**A — from GitHub (recommended; the branch is pushed).** Run from anywhere:

```bash
# clone just the installer, or use a local checkout of specify-powerpack
git clone -b "$PPBRANCH" --depth 1 https://github.com/ds1david/specify-powerpack.git /tmp/ppk-src
python /tmp/ppk-src/install.py \
  --repository https://github.com/ds1david/specify-powerpack.git \
  --ref "$PPBRANCH" \
  --project "$PP" \
  --integration codex          # or: claude
```

`install.py` does `uv tool install --force git+<repo>@<ref>` then
`specify-powerpack init "$PP" --integration <x>`. `install.sh` / `install.ps1` forward the
same flags (`bash install.sh --repository … --ref … --project "$PP" --integration codex`),
so this is also the Windows path (`.\install.ps1 --repository … --ref … --project C:\path
--integration codex`).

**B — from a local checkout (editable, no uv/network).** In your `specify-powerpack`
checkout on `$PPBRANCH`:

```bash
pip install -e .
specify-powerpack init "$PP" --integration codex     # first install (also runs `specify init` if needed)
# or, if $PP is already a Spec Kit project:
specify-powerpack install "$PP" --integration codex
```

**C — refresh an existing install to this branch.** In `$PP`, after `pip install -e .`
(or `uv tool install git+…@$PPBRANCH`) of the branch:

```bash
specify-powerpack install "$PP" --integration codex --reset-config
```

`--reset-config` rewrites `prerequisites.json` / `model-routing.json` to the **new baseline
shape** (schema 2, `implementation-evidence`, `stages == {implement-review}`); omit it to
keep an existing ChatGPT-Project binding.

**Verify the install (any path):**

```bash
ls "$PP/.specify/powerpack/bin/"                                   # expect: capabilities.py powerpack.py review_protocol.py
find "$PP" -path '*powerpack-core*commands*' -name 'speckit*.md'   # expect: only speckit.implement-review.md
grep -RnE 'debt\.py|full_cycle\.py|checklist-converge|speckit\.(implement|converge|full-cycle|debt-)' \
  "$PP/.specify/powerpack/" || echo "clean"
```

### 2.1 Prerequisite matrix

| # | What | How | Validate | Evidence |
|---|------|-----|----------|----------|
| P1 | PowerPack installed **from the branch under test** into `$PP` | one of §2.0 A / B / C | exit 0; `$PP/.specify/powerpack/bin/` = exactly `powerpack.py`, `capabilities.py`, `review_protocol.py` | `bin/` listing, install log |
| P2 | `powerpack-core` command set | enumerate the integration's command dir for PowerPack commands | `== {speckit.implement-review}` (integration form `speckit-implement-review`); none of `speckit.debt-*`, `.full-cycle`, `.implement`, `.converge`, `.checklist-converge` | directory listing |
| P3 | Upstream Spec Kit commands present | `ls "$PP/.claude/skills/" \| grep -E 'speckit-(implement\|converge)'` | both exist — PowerPack delegates to them | listing |
| P4 | Codex CLI + login | `codex --version`; `codex login` | `codex` on `PATH`; `~/.codex/auth.json` exists | version, `test -f ~/.codex/auth.json` |
| P5 | Repo ↔ ChatGPT Project binding | `specify-powerpack review setup --path "$PP" --project "<id\|name>"` | prints `Repository linked to ChatGPT Project …` and `GitHub App: READY`; `review.json` has `review_backend = codex-apps-github` | command output, `review.json` |
| P6 | A feature in `$PP` implemented + committed | its `tasks.md` all `[X]`; a real non-doc change committed since the SPEC's `plan.md` | `grep -c '^- \[ \]' specs/<feature>/tasks.md` = 0 | `git log --stat` |
| P7 | A GitHub PR, head == local HEAD | push the branch, open a PR | `git rev-parse HEAD` == PR head SHA | PR URL, HEAD SHA |

> **If P4/P5/P7 are unobtainable:** run §3 (offline) + §6, record everything, and set T025's
> terminal state to `PASS (offline) / BLOCKED (environmental) for the live gate`. That is a
> legitimate conclusion — the live services are outside this repo's control.

---

## 3. Offline evidence collection (automated)

From the repo root, with `$PP` already installed (P1):

```bash
bash specs/001-single-skill-baseline/collect-t025-offline-evidence.sh "$PP" specs/<feature>
```

This script runs and captures, into `specs/001-single-skill-baseline/T025-evidence/`:

| File | Covers | Pass condition |
|------|--------|----------------|
| `P1-bin.txt` | P1 | only the 3 preserved runtimes |
| `P2-commands.txt` | P2 | command set `== {speckit.implement-review}` |
| `P3-upstream.txt` | P3 | `speckit-implement` + `speckit-converge` found |
| `S2-prereq.json` + `S2-prerequisites.json` | S2 | `implementation-evidence`, schema 2, no `checklist-converge`; `ok:true` **or** a documented `NO_*` reason |
| `S2-negatives.txt` | S2 | `TASKS_INCOMPLETE`, `NO_SPEC_BASELINE`, `NO_IMPLEMENTATION_DELTA` each reproduced |
| `S4-gate-detect.json` / `S4-gate-run.txt` | S4 | status reflects the real delta; **not** a false `NOT_APPLICABLE` |
| `S4-capabilities-grep.txt` | S4 | no `implement_runs` / `latest_implement_files` in `capabilities.py` |
| `S5-review-route.json` + `S5-stages.json` | S5 | valid Sol contract; `stages == {implement-review}` |
| `cross-cutting-grep.txt` | §4 | `clean` (or only historical prose) |
| `pytest.txt` | — | `test_implement_review_flow_survives_cleanup.py` green |

The script exits non-zero if any offline pass condition fails.

---

## 4. Live execution (manual)

Run each command from inside `$PP`. Append stdout+stderr+`exit=$?` to the matching
`T025-evidence/<step>.txt`.

### S1 — Mandatory readiness
```bash
specify-powerpack doctor . --strict-review
specify-powerpack review status --path . --live
```
**Validate:** `doctor` → `OK` for `specify` / `spec-kit-project` / `powerpack-runtime` /
`selected-executor`; `--strict-review` review lines `OK` or an attributable credential
`FAIL` (never a missing-PowerPack-file FAIL). `review status --live` reports Project +
GitHub App state with no traceback. Neither mentions `debt` / `full-cycle` /
`checklist-converge` / a PowerPack `speckit.implement|converge`.

### S3 — Phase 1 convergence (upstream)
Invoke the **upstream** Spec Kit converge for the feature (agent `/speckit-converge`).
**Validate:** reports `CONVERGED` (or appends tasks → run upstream `speckit-implement`,
converge again). It must resolve to `.claude/skills/speckit-converge/SKILL.md`, not a
missing PowerPack `speckit.converge`.

### S6 — Browserless ChatGPT Project + GitHub deep review
```bash
specify-powerpack review run --path . --pr <PR> \
  --prompt "Perform the complete Deep Review Evidence Protocol." --output review.json
```
**Validate:** Phase A resolves the immutable PR manifest and checks `local HEAD == PR head
SHA` (mismatch → fix HEAD, re-run). Phase B: Codex uses `codex_apps` MCP with a GitHub tool
call/result, no shell/web-search fallback. Terminal state ∈ {`APPROVED`, `CHANGES_REQUIRED`,
`BLOCKED`, `BLOCKED_CONFIGURATION`}. Any failure must be attributable to Codex/Project/GitHub
readiness or review content — not a missing PowerPack module/command.
**Evidence:** full output, `review.json`, exit code, and (for `BLOCKED_CONFIGURATION`) which
S1 readiness item failed.

### S7 — Protocol validation
```bash
python .specify/powerpack/bin/review_protocol.py validate --input review.json
```
**Validate:** exit 0 for a schema-`2.0` artifact, or a clear schema error — **not** an
import error. Round 2+: also `--previous <prev.json>`.

---

## 5. Legitimate blocks

Record as `BLOCKED (environmental)` — **not** a T025 failure — when the cause is: `codex
login` not done · no ChatGPT Project on the account · GitHub App/connector not authorized ·
PR head ≠ local HEAD · review budget exhausted. If the block is permanent for you, the
honest terminal state is *"offline + contract layers PASS; live browserless gate BLOCKED
(environmental)"* and T025/T051 stay open with that note.

---

## 6. What is already proven without live services (CI)

`tests/test_implement_review_flow_survives_cleanup.py` (CI-enforced) proves:

- every module/asset the flow reaches — `browserless_review` + transitive PowerPack
  imports, `powerpack_runtime.py`, `powerpack_capabilities.py`, `review_protocol.py`,
  `speckit.implement-review.md`, `deep-review-protocol.md` — carries **zero references to
  removed commands/helpers**;
- `cli` / `browserless_review` never import `powerpack_debt` / `powerpack_full_cycle`;
- `run_browserless_code_review` drives `load_project_binding` → `resolve_pull_request` →
  `resolve_spec_context` → `current_head` in a temp repo with a fake backend, failing only
  at the Codex-auth boundary with a typed `BrowserlessReviewError` (not
  Import/Attribute/Name error);
- `resolve_pull_request` still guards the PR ↔ origin match.

So the **only** thing §4 adds is empirical proof that the live Codex / ChatGPT-Project /
GitHub services respond and the deep review reaches a terminal verdict.

---

## 7. Evidence Log

`specs/001-single-skill-baseline/T025-evidence/` (create it, commit it):

```
T025-evidence/
├── RESULT.md              # the summary you fill in — see template below
├── P1-bin.txt … S5-*.json # from collect-t025-offline-evidence.sh
├── S1-doctor.txt          # manual
├── S1-review-status.txt   # manual
├── S3-converge.txt        # manual
├── S6-review-run.txt      # manual
├── review.json            # manual (S6 artifact)
└── S7-validate.txt        # manual
```

`RESULT.md` template:

```markdown
# T025 result

- Date / operator:
- Branch + commit under test:
- Target project ($PP):
- Codex CLI version:  | OS:
- ChatGPT Project id: | PR URL: | PR head SHA vs local HEAD:

| Step | Exit | Outcome | Notes / attribution |
|------|------|---------|---------------------|
| P1 |  |  |  |
| P2 |  |  |  |
| P3 |  |  |  |
| P4 |  |  |  |
| P5 |  |  |  |
| P6 |  |  |  |
| P7 |  |  |  |
| S1 doctor / review status |  |  |  |
| S2 prereq check |  |  |  |
| S3 upstream converge |  |  |  |
| S4 gate detect / run |  |  |  |
| S5 review route |  |  |  |
| S6 review run |  |  |  |
| S7 protocol validate |  |  |  |
| §4 cross-cutting grep |  |  |  |

## Verdict

- SC-003 (no removed-command/helper failure): PASS / FAIL — evidence: …
- Live browserless gate: reached terminal verdict <X> / BLOCKED (environmental) because …
- Overall T025: PASS / PASS (offline) + live BLOCKED / FAIL
```

---

## 8. Completion Checklist

- [ ] P1–P7 satisfied — or the unobtainable ones documented in `RESULT.md` with rationale
- [ ] `collect-t025-offline-evidence.sh` run; exit 0; its files committed under `T025-evidence/`
- [ ] S1 readiness: no missing-PowerPack-file failure
- [ ] S2 prereq: `implementation-evidence` check, schema 2, no `checklist-converge`; `ok:true`
      (or a documented `NO_*` reason) + the three negatives reproduced
- [ ] S3 convergence resolved to **upstream** `speckit-converge`
- [ ] S4 quality gate reflects the real delta (not a false `NOT_APPLICABLE`); no
      `implement_runs` reference in `capabilities.py`
- [ ] S5 Sol route returns a valid contract; `model-routing.json` `stages == {implement-review}`
- [ ] S6 browserless review reached a terminal state; any block is environmental and noted
- [ ] S7 protocol validator ran (exit 0 or a schema error — not an import error)
- [ ] §4 cross-cutting grep is `clean`
- [ ] `T025-evidence/RESULT.md` filled and committed
- [ ] `tasks.md` **T025** and **T051** flipped to `[X]` with `→ T025-evidence/RESULT.md`
- [ ] PR #15 description "T025 / T051" item ticked with the verdict
