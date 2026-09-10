# Quickstart: Validate the Single Skill Baseline

Run guide for confirming the cleanup landed. Details live in `contracts/` and `data-model.md`.

## Prerequisites

- Repo checked out at the implementation branch, working tree clean.
- `python -m pytest` available (`pip install -e ".[dev]"`).
- A scratch directory for clean-install checks.

## 1. Full test suite

```bash
python -m pytest -q
```

**Expect:** green. `tests/test_debt_runtime.py` and `tests/test_full_cycle_runtime.py` are
gone; `tests/test_baseline_contract.py` is present and passing.

## 2. Registration-time exact-set

```bash
python -m pytest -q tests/test_baseline_contract.py -k registration
```

**Expect:** asserts the parsed `powerpack-core` `provides.templates` name set
`== {"speckit.implement-review"}`. Add a second command to `preset.yml` locally → test
fails (regression guard works) → revert.

## 3. Clean install → install-time exact-set + no residue

> `install.py` with no `--repository` pulls from the published GitHub default branch. To
> validate **this** branch before it merges, either install editable
> (`pip install -e .` from the checkout, then `specify-powerpack install /tmp/pp-clean`) or
> pass `install.py --repository <path-to-this-checkout> --ref <branch>`.

```bash
rm -rf /tmp/pp-clean && mkdir /tmp/pp-clean
python install.py --project /tmp/pp-clean --integration codex   # add --repository . --ref <branch> pre-merge
python - <<'PY'
from pathlib import Path
base = Path("/tmp/pp-clean/.specify/powerpack")
present = sorted(p.name for p in (base / "bin").glob("*.py"))
print("bin:", present)
assert "debt.py" not in present and "full_cycle.py" not in present
for gone in ("technical-debt-policy.md","technical-debt-template.md","technical-debt.json","full-cycle.json"):
    assert not (base / gone).exists(), gone
prereq = (base / "prerequisites.json").read_text()
assert "checklist-converge" not in prereq
assert '"statuses": ["COMPLETED"]' not in prereq
print("OK: no removed-command residue")
PY
```

Then enumerate the installed `powerpack-core` command set (integration command dir) and
confirm it equals `{"speckit.implement-review"}`.

**Expect:** all assertions pass.

## 4. Installer parity

Repeat step 3 with `install.sh` (Linux/WSL/macOS) and `install.ps1` (Windows). Diff the
resulting `.specify/powerpack/` trees against the `install.py` result.

**Expect:** identical command set and asset presence across all three.

## 5. Re-based `implement-review` prerequisite

Run in a **consuming project** that has PowerPack installed (`.specify/powerpack/bin/`
present) and a completed `tasks.md` with a real code delta — not in this dev repo, which
ships the runtime under `src/` and is not self-installed:

```bash
python .specify/powerpack/bin/powerpack.py prereq check --step implement-review
```

**Expect:** `{"ok": true, ... "reason": "OK"}`, exit 0 — **without** any
`powerpack.py implement end` / `state mark implement` ever being run, and only because a
non-doc change was **committed** for this SPEC since its plan/tasks.

Negative checks:
- Uncheck a task in `tasks.md` → `TASKS_INCOMPLETE`.
- SPEC whose `plan.md`/`tasks.md` are not committed yet → `NO_SPEC_BASELINE`.
- Only docs (or nothing) committed since the SPEC base → `NO_IMPLEMENTATION_DELTA`.
- Code changed but not committed → `NO_IMPLEMENTATION_DELTA` (commit it).
- Another SPEC's code, this SPEC's `plan.md` committed afterwards → `NO_IMPLEMENTATION_DELTA`
  for this SPEC.
- No `tasks.md` → `MISSING_TASKS`.

## 6. `implement-review` still operational

Run the minimum `implement-review` flow (readiness → convergence → quality gate → Sol →
browserless review) on a fixture project.

**Expect:** readiness calls (`specify-powerpack doctor`, `review status`) succeed; Phase 1
invokes upstream `speckit-converge` / `speckit-implement`; no step fails because of a
removed command or helper.

## 7. Repository residual-reference scan (FR-016)

```bash
grep -rnE 'speckit\.(implement|converge|checklist-converge|full-cycle|debt-[a-z]+)\b|powerpack_(debt|full_cycle)|technical-debt' \
  --exclude-dir=.git --exclude-dir=specs .
```

**Expect:** every hit classifiable as `HISTORICAL_REFERENCE` (changelog / completed spec /
merged PR) or `FALSE_POSITIVE`. Zero `ACTIVE_REFERENCE` (no current wiring, no doc
advertising a removed command as available).

## 8. Docs

Open `README.md` and `docs/PROCESS_ARCHITECTURE.md`.

**Expect:** `implement-review` is the only current `powerpack-core` command described;
`FULL_CYCLE.md`, `TECHNICAL_DEBT.md`, `WEB_GITHUB_HEADLESS_PROBE.md` are gone (or clearly
dated history); no repo-root `*.har`.
