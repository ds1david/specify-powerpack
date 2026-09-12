# Repository Residual-Reference Classification — SPEC-001 (FR-016)

Scan pattern (quickstart §7):
`speckit\.(implement|converge|checklist-converge|full-cycle|debt-)` ·
`powerpack_(debt|full_cycle)` · `technical-debt` · `full-cycle.json` · `full_cycle.py` ·
`debt.py`, run over `*.py *.md *.json *.yml *.toml`, excluding `.git/`, `specs/`,
`__pycache__/`, `.venv/`, `.codegraph/`, `src/*.egg-info/`.

| Path:line | Token | Class | Justification |
|---|---|---|---|
| `.specify/workflows/speckit/workflow.yml:71` | `command: speckit.implement` | `FALSE_POSITIVE` | Upstream Spec Kit workflow registry (installed by `specify init`), refers to the upstream `speckit.implement` command. Not PowerPack-owned; out of scope. |
| `src/speckit_powerpack/assets/presets/powerpack-core/preset.yml:22-23` | `speckit.implement-review` | n/a | The **preserved** command, not a removed reference. |
| `src/speckit_powerpack/assets/runtime/powerpack_runtime.py` (comment near `changed_paths`) | `removed \`speckit.implement\` delta-capture receipt` | `HISTORICAL_REFERENCE` | Explanatory code comment describing why the git-based signal exists; does not advertise a removed command as available. |
| `tests/test_baseline_contract.py`, `tests/test_assets_contract.py`, `tests/test_install_support.py` | `speckit.implement.md`, `debt.py`, `full-cycle.json`, … | `HISTORICAL_REFERENCE` | Regression-guard assertions that these artifacts are **absent**. Required by FR-011/FR-017. |
| `docs/` (generic prose in `IMPLEMENT_REVIEW.md` etc.) | `speckit-implement` (hyphen) | `FALSE_POSITIVE` | Refers to the upstream Spec Kit predecessor command, which `implement-review` still requires. |
| Git history / merged PRs / `specs/001-single-skill-baseline/` | various | `HISTORICAL_REFERENCE` | Project history and this spec's own text; excluded from the current-contract scan by design. |

## Result

**`ACTIVE_REFERENCE == 0`** for every removed command token. No current wiring, no
discovery path, no documentation advertising a removed command as available.
