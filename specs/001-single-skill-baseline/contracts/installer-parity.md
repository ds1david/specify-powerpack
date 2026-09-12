# Contract: Installer Parity — Post-Install State

**Purpose.** FR-005 / FR-006 / FR-019 / SC-004. Every supported entrypoint must leave the
same PowerPack state in a clean target.

## Supported entrypoints (canonical integration `codex`)

| Entrypoint | Platform | Under test |
|---|---|---|
| `install.sh` | Linux / WSL / macOS | yes |
| `install.py` | any Python ≥ 3.11 | yes |
| `install.ps1` | Windows PowerShell | yes |

Cross-integration (`codex` vs `claude`) parity is assumed by inspection: `integration` only
sets `model-routing.json.active_integration` and the `specify init --integration` value; it
does not change the `powerpack-core` command set.

## Post-install invariant (all three entrypoints)

Given a fresh, Spec Kit-initialized project with no prior PowerPack install, after the
entrypoint completes:

1. **Command set** — `powerpack-core` provides exactly `{"speckit.implement-review"}`
   (see `command-inventory.md` install-time enumeration).
2. **Runtime present** — `.specify/powerpack/bin/`: `powerpack.py`, `capabilities.py`,
   `review_protocol.py`. **Absent**: `debt.py`, `full_cycle.py`.
3. **Support assets present** — `deep-review-protocol.md`, `model-routing.json`,
   `review.json`, `update.json`, `prerequisites.json`, `quality-gates.json`.
   **Absent**: `technical-debt-policy.md`, `technical-debt-template.md`,
   `technical-debt.json`, `full-cycle.json`.
4. **`prerequisites.json`** — contains an `implement-review` entry using the
   `implementation-evidence` check; contains **no** `checklist-converge` entry; contains no
   `{"step": "implement", "statuses": ["COMPLETED"]}` requirement.
5. **`model-routing.json`** — `stages` has `implement-review`; has **no**
   `implement`, `converge`, `checklist-converge`, `full-cycle`, `debt-*` keys. (Generic
   effort tiers and `powerpack-update` retained only if still consumed by preserved code.)
6. **`powerpack-tools` extension** — installed and intact (`doctor`, `update`).
7. **No residual** — a recursive scan of `.specify/powerpack/` finds no file whose name or
   content is dedicated to a removed command.

## Re-run / reset behavior (unchanged, re-verified)

- Re-running an entrypoint on an already-installed project is idempotent for the command
  set (still `{"speckit.implement-review"}`).
- `--reset-config` (where exposed) rewrites `prerequisites.json` / `model-routing.json` to
  the new baseline shape, not the legacy one.

## Test realization

`tests/test_installer.py` / `tests/test_install_support.py` drive `install.py` /
`install_powerpack()` into `tmp_path`; the shell/PowerShell wrappers are covered by a
thin invocation test on the platform where the runner supports it, else by asserting the
wrapper delegates to the same `cli.py` entrypoint with equivalent args.
