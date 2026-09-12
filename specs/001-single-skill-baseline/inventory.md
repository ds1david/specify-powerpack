# Command Inventory Record — SPEC-001

**Baseline SHA**: `489f5355f7d2b32e50f0c0daa7b6bdb577655338` (branch `chore/spec-001-baseline-and-repo-sync`,
forked from `main`). Source of truth: `provides.templates` in
`src/speckit_powerpack/assets/presets/powerpack-core/preset.yml` at that SHA (10 command
entries), cross-checked against `commands/*.md`.

| Command | Command file | Runtime (only this cmd) | Config / assets (only this cmd) | Installer wiring (`cli.py`) | Dedicated tests | Decision |
|---|---|---|---|---|---|---|
| `speckit.implement-review` | `speckit.implement-review.md` | `powerpack_review_protocol.py`, `powerpack_capabilities.py` (shared with review flow), `deep-review-protocol.md` | `default-review.json` | copies runtime + protocol + review.json | `test_assets_contract`, `test_review_*`, `test_browserless_review`, `test_capabilities` | **PRESERVE** |
| `speckit.implement` | `speckit.implement.md` | `powerpack.py implement begin/end` + `state["steps"]["implement"]` receipt | — | `runtime_assets` (via `powerpack.py`) | `test_powerpack_runtime` (delta tests) | REMOVE (re-based: `implement_evidence`) |
| `speckit.converge` | `speckit.converge.md` | `state mark converge` | — | — | — | REMOVE (re-based: upstream `speckit-converge`) |
| `speckit.checklist-converge` | `speckit.checklist-converge.md` | `prerequisites.json` `checklist-converge` entry | — | `prerequisites.json` writer | `test_full_cycle_runtime` (skip case) | REMOVE |
| `speckit.full-cycle` | `speckit.full-cycle.md` | `powerpack_full_cycle.py` (`full_cycle.py`) | `default-full-cycle.json` (`full-cycle.json`) | `runtime_assets`, config loop | `test_full_cycle_runtime`, `test_assets_contract` | REMOVE |
| `speckit.debt-create` | `speckit.debt-create.md` | `powerpack_debt.py` (`debt.py`) | `default-technical-debt.json`, `policies/technical-debt.md`, `templates/technical-debt-backlog.md` | `runtime_assets`, doc-copy map, config loop | `test_debt_runtime`, `test_assets_contract` | REMOVE |
| `speckit.debt-list` | `speckit.debt-list.md` | `powerpack_debt.py` | (as above) | (as above) | `test_debt_runtime` | REMOVE |
| `speckit.debt-consult` | `speckit.debt-consult.md` | `powerpack_debt.py` | (as above) | (as above) | `test_debt_runtime` | REMOVE |
| `speckit.debt-start` | `speckit.debt-start.md` | `powerpack_debt.py` | (as above) | (as above) | `test_debt_runtime` | REMOVE |
| `speckit.debt-close` | `speckit.debt-close.md` | `powerpack_debt.py` | (as above) | (as above) | `test_debt_runtime` | REMOVE |

**Exactly one `PRESERVE`.**

## Shared-dependency scan (T003)

`grep -rn "powerpack_debt\|powerpack_full_cycle"` over `src/` + `tests/`: the only importers
are `cli.py` (copies them at install) and the dedicated tests `test_debt_runtime.py` /
`test_full_cycle_runtime.py`. **No preserved module imports either.** Safe to delete.

## Config-key classification (T004, rule in research.md §D3)

`default-model-routing.json` `stages` keys: only `converge` and `implement` had a live
consumer (`model route --stage` in the two deleted command docs); `cmd_model_route` looks
the stage up generically. `implement-review` is the only stage a preserved command needs.
`effort` / `integrations` / `reviewer_contract` are shared → kept. Result: `stages` and
`stage_reasons` reduced to the single `implement-review` entry.

## Upstream availability (T005)

`.claude/skills/` contains `speckit-implement` and `speckit-converge` — the re-basing
targets are present.
