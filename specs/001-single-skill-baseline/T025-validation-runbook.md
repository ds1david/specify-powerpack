# T025 — Validation Runbook: full `implement-review` flow on the single-skill baseline

**Task:** `tasks.md` T025 (US2 / SC-003). Prove the complete `speckit-implement-review`
flow runs end to end after the SPEC-001 cleanup, and that **no step fails because of a
removed command or a removed runtime helper**.

**Who runs this:** a human with live Codex + GitHub access. It cannot run in CI or an
offline sandbox.

**Where results go:** fill in [§7 Evidence Log](#7-evidence-log) and
[§8 Completion Checklist](#8-completion-checklist) below, commit this file, then flip
`- [ ] T025` → `- [X] T025` in `tasks.md` with a one-line pointer to this runbook.

---

## 1. What "pass" means

SC-003 is about **attribution**, not about the review verdict. A `CHANGES_REQUIRED` or a
`BLOCKED_CONFIGURATION` from a genuinely missing Codex/Project/GitHub credential is an
**acceptable** outcome for T025. The task **fails** only if any step dies with:

- `ModuleNotFoundError` / `ImportError` / `No such file or directory` for
  `debt.py`, `full_cycle.py`, `powerpack_debt`, `powerpack_full_cycle`,
  `technical-debt*.json`, `full-cycle.json`;
- "unknown command" / "not found" for `speckit-implement`, `speckit.implement`,
  `speckit-converge`, `speckit.converge`, `speckit-checklist-converge`,
  `speckit-full-cycle`, `speckit-debt-*` **from PowerPack** (upstream `speckit-implement` /
  `speckit-converge` are expected and fine);
- a `prereq check` that references an `implement` **state receipt** instead of the
  `implementation-evidence` check;
- the capability quality gate returning `NOT_APPLICABLE` for a change set that is clearly
  not documentation-only (the Phase 8 regression — must be fixed on the branch under test).

Capture the **exact stdout/stderr and exit code** of every command. That is the evidence.

---

## 2. Environment prerequisites

Do these once; record versions in the Evidence Log.

| # | Step | Command | Validate | Evidence |
|---|------|---------|----------|----------|
| P1 | PowerPack installed **from the branch under test** into a scratch project | `python install.py --project "$PP" --integration codex --repository <path-to-this-checkout> --ref feat/spec-001-single-skill-baseline` (or `pip install -e .` in the checkout, then `specify-powerpack install "$PP"`) | Command exits 0. `$PP/.specify/powerpack/bin/` contains **only** `powerpack.py`, `capabilities.py`, `review_protocol.py`. No `debt.py` / `full_cycle.py`. | `ls -la $PP/.specify/powerpack/bin/`, install log |
| P2 | `powerpack-core` command set | enumerate the integration command dir for PowerPack commands | Set `== {speckit.implement-review}` (or the integration equivalent, e.g. `speckit-implement-review`). No `speckit.debt-*`, `speckit.full-cycle`, `speckit.implement`, `speckit.converge`, `speckit.checklist-converge`. | directory listing |
| P3 | Upstream Spec Kit commands present | `ls "$PP/.claude/skills/" \| grep -E 'speckit-(implement\|converge)'` (or the active integration's dir) | Both `speckit-implement` and `speckit-converge` exist (PowerPack now delegates to them). | listing |
| P4 | Codex CLI + login | `codex --version` ; `codex login` (interactive) | `codex` on `PATH`; login completes; `~/.codex/auth.json` exists. | version string, `test -f ~/.codex/auth.json` |
| P5 | Repo ↔ ChatGPT Project binding | `specify-powerpack review setup --path "$PP" --project "<id-or-name>"` | Prints `Repository linked to ChatGPT Project '<name>' (<id>)` and `GitHub App: READY`. Writes `$PP/.specify/powerpack/review.json` with `review_backend = codex-apps-github`. | command output, `jq . review.json` |
| P6 | A feature implemented in `$PP` with a completed `tasks.md` | — | `$PP/specs/<feature>/tasks.md` exists and every `- [ ]`/`- [x]` task line is `[X]`; there is a real non-doc code change on the branch. | `grep -c '^- \[ \]' tasks.md` = 0 |
| P7 | A GitHub PR whose head == local HEAD | push the branch, open a PR | PR number known; `git rev-parse HEAD` == PR head SHA. | PR URL, `git rev-parse HEAD` |

> If P4/P5 cannot be satisfied, T025 can still be **partially** recorded: run P1–P3 + steps
> S1–S4 below (which don't need Codex/GitHub) and mark T025 as "core flow validated;
> browserless gate pending credentials", citing the static tests
> (`test_browserless_review.py`, `test_review_*`) for the remainder.

---

## 3. Step-by-step execution

Run every command from **inside `$PP`**. Copy stdout, stderr, and `echo "exit=$?"` into the
Evidence Log for each.

### S1 — Mandatory readiness

```bash
specify-powerpack doctor . --strict-review
specify-powerpack review status --path . --live
```

**Validate:**
- `doctor` prints `OK` for `specify`, `spec-kit-project`, `powerpack-runtime`,
  `selected-executor`; with `--strict-review`, the review-readiness lines are `OK` (or a
  clearly-attributable `FAIL` on a missing external credential — not a missing PowerPack file).
- `review status --live` reports the Project + GitHub App state without a traceback.
- **SC-003 check:** neither command references `debt`, `full-cycle`, `full_cycle.py`,
  `checklist-converge`, or a PowerPack `speckit.implement` / `speckit.converge`.

**Evidence:** full output of both commands + exit codes.

### S2 — Re-based prerequisite gate

```bash
python .specify/powerpack/bin/powerpack.py prereq check --step implement-review --feature-dir specs/<feature>
```

**Validate:**
- Exit `0` and JSON `{"ok": true, "step": "implement-review", "reason": "OK", ...}`.
- The `prerequisites.json` in use has `"schema_version": 2` and
  `"implement-review": [{"check": "implementation-evidence"}]` — **no** `implement` receipt
  requirement, **no** `checklist-converge` entry.
- Negative sanity (optional, revert after): uncheck one task in `tasks.md` → expect
  `{"ok": false, "reason": "TASKS_INCOMPLETE", "unchecked": N}`; re-check it.

**Evidence:** the JSON, exit code, and `jq . .specify/powerpack/prerequisites.json`.

### S3 — Phase 1 convergence (upstream)

Run the upstream Spec Kit converge for the same feature (the agent command
`/speckit-converge`, or however the integration invokes it):

```text
speckit-converge        # upstream Spec Kit — NOT a PowerPack command
```

**Validate:**
- It runs and reports `CONVERGED` (or appends tasks — then run upstream `speckit-implement`
  for that work and converge again).
- **SC-003 check:** the invocation resolves to the **upstream** `speckit-converge` skill,
  not a missing PowerPack `speckit.converge`. `speckit.implement-review.md` §"Phase 1"
  and its line "Throughout this document `speckit-implement` and `speckit-converge` are the
  **upstream Spec Kit** commands" should match what actually ran.

**Evidence:** converge output / handoff line; note which skill file resolved
(`.claude/skills/speckit-converge/SKILL.md` vs a 404).

### S4 — Capability quality gate

```bash
python .specify/powerpack/bin/capabilities.py gate detect --feature-dir specs/<feature>
python .specify/powerpack/bin/capabilities.py gate run    --feature-dir specs/<feature>
```

**Validate:**
- `gate detect` returns a `status` reflecting the **real** change set:
  `REQUIRED` (with a build command) or `BLOCKED_CONFIGURATION` for an unknown architecture —
  **not** `NOT_APPLICABLE`, unless the delta genuinely is documentation-only.
- This is the **Phase 8 regression point**: confirm `capabilities.py` sources the change
  list from git (`changed_paths`), not from `implement_runs`. Quick proof: `grep -n
  "implement_runs\|latest_implement_files" .specify/powerpack/bin/capabilities.py` → **no
  matches**.
- `gate run` executes the resolved command and returns its real exit code.

**Evidence:** both JSON outputs, `gate run` exit code, the grep result.

### S5 — Independent Sol review route

```bash
python .specify/powerpack/bin/powerpack.py review route
```

**Validate:**
- Returns an executor-aware route (`reviewer_mode`, contract `gpt-5.6-sol/xhigh/read-only`).
- No traceback; no reference to removed stages in `model-routing.json`
  (`jq '.stages' .specify/powerpack/model-routing.json` → `{"implement-review":"orchestration"}`).

**Evidence:** route JSON, `jq '.stages'` output.

### S6 — Browserless ChatGPT Project + GitHub deep review

```bash
specify-powerpack review run \
  --path . \
  --pr <PR-number-or-URL> \
  --prompt "Perform the complete Deep Review Evidence Protocol." \
  --output review.json
```

**Validate:**
- Phase A: PowerPack resolves the immutable PR manifest and verifies
  `local HEAD == PR head SHA`. A mismatch **blocks** — that is correct behaviour, fix HEAD
  and re-run.
- Phase B: Codex inspects the PR through `codex_apps` MCP (GitHub tool call/result present
  in the transcript); no shell / web-search fallback.
- Terminal state is one of `APPROVED` / `CHANGES_REQUIRED` / `BLOCKED` / `BLOCKED_CONFIGURATION`.
- **SC-003 check:** any failure is attributable to Codex/Project/GitHub readiness or review
  content — **not** to a missing PowerPack module/command.

**Evidence:** full `review run` output, `review.json`, exit code. If `BLOCKED_CONFIGURATION`,
record which readiness item failed (from S1).

### S7 — Protocol validation

```bash
python .specify/powerpack/bin/review_protocol.py validate --input review.json
```

**Validate:** exits 0 for a schema-`2.0` artifact (or a clear schema error — not an import
error). If a round 2 was run: `--previous <prev.json>` also validates.

**Evidence:** validator output + exit code.

---

## 4. Cross-cutting SC-003 assertion

After S1–S7, run once in `$PP`:

```bash
grep -rnE 'debt\.py|full_cycle\.py|powerpack_debt|powerpack_full_cycle|technical-debt|speckit\.(implement|converge|full-cycle|debt-)' \
  .specify/powerpack/ 2>/dev/null || echo "clean"
```

**Validate:** `clean` (or only historical strings inside `deep-review-protocol.md` prose).
No installed runtime file or command references a removed capability.

---

## 5. If a step legitimately blocks

Record it as **BLOCKED (environmental)**, not a T025 failure, when the cause is:
`codex login` not completed · no ChatGPT Project available for the account · GitHub App /
connector not authorized for the repo · PR head ≠ local HEAD · review budget exhausted.

T025 is only **failed** when the cause is a removed PowerPack command/helper (see §1).

---

## 6. Minimal path (no Codex/GitHub yet)

If credentials are unavailable, this still closes the *code* half of T025:

1. P1–P3, S2, S4, S5, §4 — all runnable offline in a temp installed project.
2. Mark T025: *"Core `implement-review` flow (readiness plumbing, re-based prereq, capability
   gate, Sol route) validated on a clean install with zero removed-command references. S1
   partial (no live review creds), S3/S6/S7 pending live Codex+GitHub; covered statically by
   `tests/test_browserless_review.py`, `tests/test_review_context.py`,
   `tests/test_review_protocol.py`, `tests/test_codex_apps_runtime.py`."*

---

## 7. Evidence Log

> Paste command output verbatim. Keep exit codes.

| Step | Command | Exit | Result summary | Evidence file / paste |
|------|---------|------|----------------|-----------------------|
| P1 | `install.py …` | | | |
| P2 | command-set enumeration | | | |
| P3 | upstream skills present | | | |
| P4 | `codex --version` / `codex login` | | | |
| P5 | `review setup` | | | |
| P6 | tasks complete + code delta | | | |
| P7 | PR head == HEAD | | | |
| S1 | `doctor --strict-review` | | | |
| S1 | `review status --live` | | | |
| S2 | `prereq check --step implement-review` | | | |
| S3 | upstream `speckit-converge` | | | |
| S4 | `capabilities.py gate detect` | | | |
| S4 | `capabilities.py gate run` | | | |
| S4 | grep `implement_runs` in `capabilities.py` | | (expect: no matches) | |
| S5 | `powerpack.py review route` | | | |
| S6 | `review run --pr …` | | | |
| S7 | `review_protocol.py validate` | | | |
| §4 | cross-cutting grep | | (expect: clean) | |

**Environment:** Codex CLI version ▢ · OS ▢ · branch/commit under test ▢ · target project ▢ ·
ChatGPT Project id ▢ · PR URL ▢ · date ▢ · operator ▢

---

## 8. Completion Checklist

- [ ] P1–P7 satisfied (or §6 minimal path taken and documented)
- [ ] S1 readiness: no missing-PowerPack-file failure
- [ ] S2 prereq: `implementation-evidence` check, `ok:true`, schema 2, no `checklist-converge`
- [ ] S3 convergence resolved to **upstream** `speckit-converge`
- [ ] S4 quality gate reflects the real delta (not a false `NOT_APPLICABLE`); no `implement_runs` ref
- [ ] S5 Sol route returns a valid contract; `model-routing.json` stages == `{implement-review}`
- [ ] S6 browserless review reached a terminal state; any block is environmental
- [ ] S7 protocol validator ran (0 or a schema error, not an import error)
- [ ] §4 cross-cutting grep is clean
- [ ] Evidence Log filled and committed
- [ ] `tasks.md` T025 flipped to `[X]` with a pointer to this file
