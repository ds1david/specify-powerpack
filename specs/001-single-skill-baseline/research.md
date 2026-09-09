# Phase 0 Research: Single Skill Baseline

All items below were resolved from the repository itself (no external research needed).

## D1 — Re-basing the `implement-review` prerequisite gate

**Context.** Today `speckit.implement-review.md` runs
`powerpack.py prereq check --step implement-review`. `cmd_prereq_check` →
`evaluate_receipt(root, feature, "implement", {"COMPLETED"})` reads
`.specify/powerpack/<feature>/state.json → steps.implement.status`. That `COMPLETED` receipt
is written **only** by `cmd_implement_end` (`powerpack.py implement end`), which
`speckit.implement.md` instructs the agent to run. Removing `speckit.implement` removes the
only writer of that receipt.

**Investigated.** `.claude/skills/speckit-implement/SKILL.md` (upstream): it marks
`tasks.md` items `[X]` and reports completion. It writes **no** machine-readable PowerPack
state, no marker file, no `.specify/` receipt. So there is no upstream signal to key a
receipt-style gate on.

**Decision.** Re-base the gate onto **repository evidence**, evaluated live:

1. `FEATURE_DIR/tasks.md` exists, and every task checkbox line (`- [ ]` / `- [x]`) is
   checked `[X]` — i.e. an implementation pass has been carried through to completion.
2. A **non-documentation implementation delta** exists for the active SPEC: at least one
   changed non-doc file since `plan.md` was authored, using the primitives already in
   `powerpack_runtime.py` (`git_candidate_files`, `workspace_snapshot`, `sha_file`,
   `is_documentation_only`, `git_head`). This preserves the original intent
   ("`implement-review` never performs the initial implementation merely to satisfy its own
   prerequisite" — a real prior implementation must exist) without a PowerPack predecessor
   command.

Implementation shape: `cmd_prereq_check` keeps its interface; for `--step implement-review`
it calls a new `implement_evidence(root, feature) -> {"ok", "reason", ...}` evaluator
instead of `evaluate_receipt(..., "implement", ...)`. `default_prerequisites()` and the
`prerequisites.json` written by `cli.py` no longer contain an `implement` receipt
requirement for `implement-review` (and drop `checklist-converge` entirely).

**Rationale.** Faithful to FR-018 ("satisfiable from an upstream `speckit-implement` run");
uses only code already present; no shim; the appended-tasks loop in `implement-review`
Phase 1 still works (re-running upstream `speckit-implement` re-checks all boxes, delta
grows).

**Alternatives considered.**
- *Keep a thin user-invoked `powerpack.py implement end` receipt.* Rejected: it is the
  removed wrap's mechanism wearing a different hat; friction; drifts toward FR-014.
- *Gate purely on `tasks.md` all-`[X]`.* Rejected as the sole signal — checkboxes can be
  toggled without real work (weak, against the spirit of R-004). The delta check closes
  that.
- *Delete the gate entirely.* Rejected: `implement-review` explicitly must prove an
  explicit prior implementation (its "Mandatory predecessor" and "Completion" sections).

**Edge cases for `contracts/implement-review-prereq.md`:** no `tasks.md` → fail
`MISSING_TASKS`; some boxes unchecked → fail `TASKS_INCOMPLETE` (report count); boxes all
checked but only docs changed → fail `NO_IMPLEMENTATION_DELTA`; not a git repo → degrade to
tasks-only with a `git_unavailable: true` note (do not hard-block CI/offline).

## D2 — Re-basing `implement-review` convergence (Phase 1 loop)

**Context.** `speckit.implement-review.md` Phase 1: "Run `speckit-converge` … tasks
appended → run `speckit-implement` … then converge again." `speckit.converge.md` wraps
"official Spec Kit converge" and records `state mark converge --status CONVERGED`.

**Decision.** The `implement-review` prose calls upstream **`speckit-converge`** and
**`speckit-implement`** by their exact upstream skill names (note: `speckit-converge`, not
`speckit.converge`). The `state mark converge` receipt is dropped — nothing that survives
reads a `converge` receipt (`cmd_prereq_check` only had `checklist-converge` and
`implement-review` requirements; both are being changed/removed). `implement-review`
determines convergence from the upstream command's own report, exactly as it already treats
Sol/deep-review outcomes.

**Rationale.** `speckit.converge` added only a model-route preflight and a receipt with no
downstream consumer after this cleanup. Upstream `speckit-converge` is present in
`.claude/skills/`.

**Alternative considered.** Keep `speckit.converge` as a preserved dependency (Q1 option
A). Rejected by the clarification session (answer B).

**Follow-through (FR-016 / repo verification).** Because `speckit-implement` (upstream) and
`speckit.implement` (removed) differ by one character, the prose rewrite must be explicit
and a review task must confirm no remaining reference implies the *removed* wrap. The
`ACTIVE_REFERENCE == 0` grep must match the dotted form `speckit.implement` /
`speckit.converge` and the `speckit.implement.md` / `speckit.converge.md` filenames, not
the hyphenated upstream names.

## D3 — Authoritative command-set enumeration

**Context.** `test_assets_contract.py` currently asserts by **filename presence**
(`(commands / "speckit.implement-review.md").is_file()`) and by substring match in
`preset.yml`. `test_debt_and_full_cycle_commands_are_packaged` asserts the *presence* of
every command being deleted.

**Decision.** The single source of truth for "PowerPack-provided command" is the list of
`provides.templates[].name` values in
`src/speckit_powerpack/assets/presets/powerpack-core/preset.yml`. Tests parse that YAML
block (stdlib: a minimal parser or `preset.yml` is already simple `key: "value"` lines —
prefer a tiny regex/scan over adding a YAML dep, matching the stdlib-only rule for shipped
code; tests may use any stdlib approach). Install-time enumeration reads the same names from
the copy Spec Kit registers (or from the generated command files under the integration's
command dir), and asserts equality with `{"speckit.implement-review"}`.

**Rationale.** Filenames and substring matches let a stale command survive silently
(FR-004, FR-011). One canonical parsed list makes the equality assertion unambiguous.

**Config-key classification rule (for T004 / CHK007).** A key in
`config/default-model-routing.json` (`stages`, `stage_reasons`, and any per-stage override)
is *removed-command-specific* — and MUST be deleted — **iff** its stage name is a removed
command (`implement`, `converge`, `checklist-converge`, `full-cycle`, `debt-*`,
`powerpack-update` when the `update` command no longer references routing) **and** no
preserved code path resolves that stage name (grep `cmd_model_route` and its callers plus
the preserved command docs for the literal). Everything else — the `effort` tiers,
`integrations`, `reviewer_contract`, and the `implement-review` stage — is shared and stays.
This is a mechanical grep-backed decision, not a judgement call.

## D4 — `powerpack-tools` extension

**Decision.** Preserve `src/speckit_powerpack/assets/extensions/powerpack-tools/` intact:
`speckit.powerpack-tools.doctor` (an operational prerequisite of `implement-review`'s
"Mandatory readiness") and `speckit.powerpack-tools.update`. It is a separate namespace from
the `powerpack-core` preset; the exact-set assertion (FR-011) is scoped to `powerpack-core`.
Only trim removed-command references inside `commands/update.md` if present.

**Rationale.** Clarification session answer (Q3 = A). The extension is runtime
infrastructure, not a product capability.

## D5 — Installer parity scope

**Decision.** Officially supported and validated: `install.sh`, `install.py`, `install.ps1`
against the canonical integration (`codex`, `DEFAULT_INTEGRATION` in `cli.py`). Each must
produce `powerpack-core` command set `{"speckit.implement-review"}` and no removed-command
asset under `.specify/powerpack/`. `install.sh` and `install.ps1` are thin wrappers over the
same `cli.py` install path; `codex` vs `claude` integration parity is assumed by inspection
of `install_support()` (integration only sets `active_integration` in `model-routing.json`).

**Rationale.** Clarification session answer (Q4 = A). Full 3×2 matrix e2e is disproportionate
for wrappers over one code path.

## D6 — Documentation strategy

**Decision.**
- **Delete** command-dedicated pages whose subject is fully removed: `docs/FULL_CYCLE.md`,
  `docs/TECHNICAL_DEBT.md`, `docs/WEB_GITHUB_HEADLESS_PROBE.md`.
- **Scrub** current-state docs to present `implement-review` as the only current
  `powerpack-core` command: `README.md`, `docs/PROCESS_ARCHITECTURE.md`,
  `docs/CUSTOMIZATION.md`, `docs/DECISIONS_AND_TRADEOFFS.md`, `docs/INSTALLATION.md`,
  `docs/PORTABILITY.md`, `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`.
- **Keep + cross-ref update**: `docs/IMPLEMENT_REVIEW.md`,
  `docs/CHATGPT_GITHUB_BROWSERLESS_SMOKE.md`, `docs/CODEX_FIRST_INSTALL.md`,
  `docs/PROJECT_EVOLUTION.md`.
- **History** that is worth keeping (e.g. a changelog line, a completed-SPEC reference) may
  stay only if it does not read as current support (FR-008). `specs/` history is untouched.

**Rationale.** FR-007 / FR-008. The `PROJECT_EVOLUTION.md` policy (PR #10) already frames
removed capability as a scope decision, not a defect.

## D7 — Removal inventory (baseline SHA `489f5355`)

Files that exist **solely** for a removed command (delete):

| Area | Paths |
|---|---|
| Preset command docs | `assets/presets/powerpack-core/commands/speckit.{implement,converge,checklist-converge,full-cycle,debt-create,debt-list,debt-consult,debt-start,debt-close}.md` |
| Runtime | `assets/runtime/powerpack_debt.py`, `assets/runtime/powerpack_full_cycle.py` |
| Config / policy / template | `assets/config/default-full-cycle.json`, `assets/config/default-technical-debt.json`, `assets/policies/technical-debt.md`, `assets/templates/technical-debt-backlog.md` |
| Tests | `tests/test_debt_runtime.py`, `tests/test_full_cycle_runtime.py`, `tests/test_assets_contract.py::test_debt_and_full_cycle_commands_are_packaged` (+ related assertions) |
| Homologation | `scripts/homologation/probe_*.py`, repo-root `*.har`, `docs/WEB_GITHUB_HEADLESS_PROBE.md` |
| Docs | `docs/FULL_CYCLE.md`, `docs/TECHNICAL_DEBT.md` |

Files that are **edited** (shared surface, removed-command parts stripped):

| Path | Change |
|---|---|
| `assets/presets/powerpack-core/preset.yml` | `provides.templates` → only `speckit.implement-review` |
| `assets/presets/powerpack-core/commands/speckit.implement-review.md` | re-base Phase 1 / predecessor prose onto upstream names |
| `assets/runtime/powerpack_runtime.py` | drop `implement begin/end` subcommands + wrap-only `state mark` paths; add `implement-review` evidence evaluator; drop `checklist-converge` from `default_prerequisites()` |
| `assets/config/default-model-routing.json` | keep `implement-review` + generic runtime stages; drop `implement`, `converge`, `checklist-converge`, `full-cycle`, `debt-*`, `powerpack-update` (keep `powerpack-update` **only if** still referenced by the preserved `update` command — verify during tasks) |
| `cli.py` `install_support()` | stop copying `debt.py`, `full_cycle.py`, `technical-debt-policy.md`, `technical-debt-template.md`, `technical-debt.json`, `full-cycle.json`; rewrite `prerequisites.json` default |
| `tests/test_assets_contract.py`, `tests/test_installer.py`, `tests/test_install_support.py`, `tests/test_powerpack_runtime.py` | exact-set assertions; drop removed-command cases |
| current-state docs (D6 list) | scrub |

Files explicitly **kept** (shared infra / `implement-review` deps): `powerpack_runtime.py`
(generic surface), `powerpack_capabilities.py`, `powerpack_review_protocol.py`,
`assets/review/deep-review-protocol.md`, `assets/config/default-review.json`,
`assets/config/default-update.json`, `assets/extensions/powerpack-tools/**`, `browserless_review.py`,
`chatgpt_project_provider.py`, `github_*` modules, `codex_apps*`, `capabilities`/`review`
tests, `scripts/homologation/smoke_chatgpt_github_browserless.py`.

**Open verification for `/speckit-tasks`:** confirm nothing preserved imports
`powerpack_debt` / `powerpack_full_cycle`; confirm `default-model-routing.json` generic
stages (`economical`, `coding`, …) are still consumed by `cmd_model_route`; confirm
`egg-info/SOURCES.txt` regenerates (build artifact, not hand-edited).

## Baseline confirmation (implementation, 2026-09-09)

Implementation started from `489f5355f7d2b32e50f0c0daa7b6bdb577655338` (branch
`chore/spec-001-baseline-and-repo-sync`). No inventory delta vs the SHA recorded in
`spec.md` — the preset still had the same 10 command entries. Full per-command decisions,
the shared-dependency scan and the config-key classification are in `inventory.md`; the
residual-reference scan is in `reference-classification.md` (0 `ACTIVE_REFERENCE`).
