---
description: "Task list for feature implementation"
---

# Tasks: Single Skill Baseline

**Input**: Design documents from `specs/001-single-skill-baseline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec explicitly requires contract + regression tests
(FR-010, FR-011, FR-017) and the re-based gate (FR-018) needs its own coverage. Test tasks
for the exact-set contract and the re-based prereq are written **before** the deletions they
guard (R-006).

**Organization**: By user story. US1 + US2 are both P1 and together form the MVP.

**Implementation status (2026-09-09)**: T001–T024, T026–T039, T041–T043 complete on branch
`chore/spec-001-baseline-and-repo-sync`; `pytest` = 90 passed. Not auto-completable here:
**T025** (live Codex + ChatGPT Project + GitHub PR needed), **T040 §4–§6** (Windows runner /
live env), **T045** (reviewer sign-off). Static parts of the
quickstart (§1–§3, §7, §8) were walked and pass.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 from spec.md; Setup/Foundational/Polish carry no story label

## Path Conventions

Single project. Asset tree: `src/speckit_powerpack/assets/`. Tests: `tests/`. Repo root
holds `install.sh` / `install.py` / `install.ps1`, `README.md`, `AGENTS.md`, `CLAUDE.md`.

---

## Phase 1: Setup — Inventory & Baseline (no deletions yet)

**Purpose**: Produce the pre-deletion decision record (FR-002) and pin the baseline.

- [X] T001 Record the actual implementation baseline SHA (current `main` = `489f5355f7d2b32e50f0c0daa7b6bdb577655338`) and note any inventory delta vs `a825557` in `specs/001-single-skill-baseline/research.md` §D7 (append a short "Baseline confirmation" note).
- [X] T002 [P] Build the Command Inventory Record (one row per `provides.templates` entry in `src/speckit_powerpack/assets/presets/powerpack-core/preset.yml`) as `specs/001-single-skill-baseline/inventory.md`, using the field set in `data-model.md` §Command Inventory Record; mark only `speckit.implement-review` as `PRESERVE`.
- [X] T003 [P] Shared-dependency scan: grep the repo for `import powerpack_debt`, `import powerpack_full_cycle`, `from .powerpack_debt`, `powerpack_full_cycle`, and record in `inventory.md` every consumer; confirm no PRESERVE asset imports either module (FR-013, R-003, research.md §D7 open-verification).
- [X] T004 [P] Config-key classification: in `inventory.md`, classify every key in `src/speckit_powerpack/assets/config/default-model-routing.json` (`stages` + `stage_reasons` + `effort` tiers) as removed-command-only vs shared-runtime (consumed by `cmd_model_route` / preserved code) — resolves CHK007.
- [X] T005 [P] Confirm upstream `speckit-implement` and `speckit-converge` skills are present under `.claude/skills/` (or the active integration's command dir) and note it in `inventory.md` as the re-basing target (CHK038).

**Checkpoint**: `inventory.md` complete; exactly one `PRESERVE`; shared deps identified.

---

## Phase 2: Foundational — Re-base `implement-review`, then failing guard tests

**⚠️ CRITICAL**: T006–T009 (re-basing) MUST land before any `speckit.implement` /
`speckit.converge` deletion in Phase 5. T010–T013 are written to FAIL now and pass after
Phase 3/6.

- [X] T006 Add an evidence-based prerequisite evaluator to `src/speckit_powerpack/assets/runtime/powerpack_runtime.py`: `implement_evidence(root, feature) -> dict` implementing the algorithm in `contracts/implement-review-prereq.md` (tasks.md present + all checkboxes `[X]` + non-documentation delta via existing `git_candidate_files` / `workspace_snapshot` / `is_documentation_only`; degrade to tasks-only with `git_unavailable: true` when git absent).
- [X] T007 Rewire `cmd_prereq_check` in `src/speckit_powerpack/assets/runtime/powerpack_runtime.py` so `--step implement-review` calls `implement_evidence(...)` instead of `evaluate_receipt(..., "implement", {"COMPLETED"})`; keep the JSON output shape and non-zero exit + `next_action: "speckit-implement"`; treat a legacy `{"step":"implement","statuses":["COMPLETED"]}` config entry as "use `implementation-evidence`" (forward-compat).
- [X] T008 Update `default_prerequisites()` in `src/speckit_powerpack/assets/runtime/powerpack_runtime.py` and the `prerequisites.json` writer in `src/speckit_powerpack/cli.py` (`install_support`): remove the `checklist-converge` entry entirely; set `implement-review` to `[{"check": "implementation-evidence"}]`; bump `schema_version` to 2.
- [X] T009 Rewrite the predecessor/convergence prose in `src/speckit_powerpack/assets/presets/powerpack-core/commands/speckit.implement-review.md`: "Mandatory predecessor" and Phase 1 must name upstream `speckit-implement` / `speckit-converge` (hyphen) explicitly, drop references that read as the removed `speckit.implement` / `speckit.converge` wraps, and drop the `state mark converge` step (FR-018, research.md §D2, CHK018–019).
- [X] T010 [P] Write `tests/test_powerpack_runtime.py` cases for `implement_evidence`: `OK`, `MISSING_TASKS`, `TASKS_INCOMPLETE` (with `unchecked` count), `NO_IMPLEMENTATION_DELTA` (docs-only change), and `git_unavailable` degrade path. Remove the old `implement begin/end` receipt-gate cases.
- [X] T011 [P] Write `tests/test_baseline_contract.py::test_registration_command_set`: parse `provides.templates[].name` from `preset.yml` and assert `== {"speckit.implement-review"}` (equality). Currently FAILS.
- [X] T012 [P] Write `tests/test_baseline_contract.py::test_installed_command_set`: `install_powerpack` into `tmp_path` (integration `codex`), enumerate `powerpack-core` commands per `contracts/command-inventory.md`, assert `== {"speckit.implement-review"}` and `no_removed_command_assets_under(.specify/powerpack)`. Currently FAILS.
- [X] T013 [P] Write `tests/test_installer.py` / `tests/test_install_support.py` assertions that `debt.py`, `full_cycle.py`, `technical-debt-policy.md`, `technical-debt-template.md`, `technical-debt.json`, `full-cycle.json` are ABSENT post-install and `prerequisites.json` contains no `checklist-converge` / no `"statuses": ["COMPLETED"]`. Currently FAIL.

**Checkpoint**: `pytest -k "implement_evidence or baseline_contract"` runs; new gate tests
green, exact-set tests red (expected until Phase 3).

---

## Phase 3: US1 — Clean install exposes only `implement-review` (Priority: P1) 🎯 MVP

**Goal**: `powerpack-core` registers and installs exactly `{"speckit.implement-review"}`.

**Independent test**: run each installer into a clean target → enumerate → set equality;
scan for residual assets.

- [X] T014 [US1] Edit `src/speckit_powerpack/assets/presets/powerpack-core/preset.yml`: reduce `provides.templates` to the single `speckit.implement-review` command entry; remove `implement`, `converge`, `checklist-converge`, `full-cycle`, `debt-*` entries; keep `requires` / `tags`.
- [X] T015 [US1] Delete removed command docs: `src/speckit_powerpack/assets/presets/powerpack-core/commands/speckit.implement.md`, `speckit.converge.md`, `speckit.checklist-converge.md`, `speckit.full-cycle.md`, `speckit.debt-create.md`, `speckit.debt-list.md`, `speckit.debt-consult.md`, `speckit.debt-start.md`, `speckit.debt-close.md`.
- [X] T016 [US1] Edit `src/speckit_powerpack/cli.py` `install_support()`: drop `runtime/powerpack_debt.py` and `runtime/powerpack_full_cycle.py` from `runtime_assets`; drop `policies/technical-debt.md` and `templates/technical-debt-backlog.md` from the doc-copy map; drop `config/default-technical-debt.json` and `config/default-full-cycle.json` from the config loop. Keep `deep-review-protocol.md`, `default-review.json`, `default-update.json`.
- [X] T017 [US1] Edit `src/speckit_powerpack/assets/config/default-model-routing.json` per T004 classification: keep `implement-review` + shared effort tiers/integrations; remove `implement`, `converge`, `checklist-converge`, `full-cycle`, `debt-*` from `stages` and `stage_reasons`; remove `powerpack-update` only if T004 shows it is unreferenced by the preserved `update` command.
- [X] T018 [US1] Remove the `implement begin` / `implement end` argparse subcommands and `cmd_implement_begin` / `cmd_implement_end` from `src/speckit_powerpack/assets/runtime/powerpack_runtime.py`; keep `review` / `limit` / `gate` / `model` subcommands. For `state mark` / `state check` and the `workspace_snapshot` / `snapshot_delta` helpers: grep the preserved asset tree + `speckit.implement-review.md` for a surviving consumer — remove them too if none remains, otherwise keep and add a one-line comment naming the consumer (resolves analyze D1 / CHK011). May be done right after T007 (same file) to avoid a test-less window.
- [X] T019 [US1] Verify `install.sh`, `install.py`, `install.ps1` at repo root contain no removed-command wiring; if a wrapper names a removed command/asset, remove that reference (FR-005).
- [X] T020 [US1] Run `python -m pytest tests/test_baseline_contract.py tests/test_installer.py tests/test_install_support.py` — the exact-set + residual-absence tests from Phase 2 now PASS.

**Checkpoint**: Clean install of all 3 entrypoints yields `{"speckit.implement-review"}`
(quickstart §3–§4).

---

## Phase 4: US2 — `implement-review` still works end to end (Priority: P1) 🎯 MVP

**Goal**: the one preserved capability is unbroken by the removals.

**Independent test**: minimum `implement-review` flow on a fixture project reaches its
terminal state; re-based prereq passes without any PowerPack `implement` receipt.

- [X] T021 [P] [US2] Confirm KEEP assets are still copied by `install_support()` and present post-install: `powerpack.py`, `capabilities.py`, `review_protocol.py`, `deep-review-protocol.md`, `model-routing.json`, `review.json`, `update.json`, `prerequisites.json`, `quality-gates.json` (contracts/installer-parity.md §2–§3).
- [X] T022 [P] [US2] Confirm the `powerpack-tools` extension (`src/speckit_powerpack/assets/extensions/powerpack-tools/`) is untouched and still provides `doctor` + `update`; trim only removed-command references inside `commands/update.md` if any exist (CHK004, D4).
- [X] T023 [US2] Update `tests/test_powerpack_runtime.py` (and any review/capabilities test) so the `implement-review` readiness + prereq path uses the re-based evidence gate; add a case proving `prereq check --step implement-review` returns `ok:true` with only a completed `tasks.md` + code delta present (no `state mark implement`).
- [X] T024 [US2] Keep `scripts/homologation/smoke_chatgpt_github_browserless.py` and `src/speckit_powerpack/github_browserless_smoke.py` / `github_connector_preflight.py`; run the browserless smoke (or its contract test `tests/test_browserless_review.py`) to confirm the deep-review gate still functions (FR-020).
- [ ] T025 [US2] Execute quickstart §6 on a fixture project: readiness (`specify-powerpack doctor`, `review status`) → convergence via upstream `speckit-converge` → quality gate → Sol route → browserless review; record that no step fails due to a removed command/helper (SC-003). **Blocked on live env**: needs Codex login, a repo↔ChatGPT-Project binding and a real GitHub PR. Static coverage in place: `test_powerpack_runtime` (evidence gate, gate detection), `test_browserless_review`, `test_review_*`. **Execution runbook:** `T025-validation-runbook.md` (steps, per-step validation, evidence log).

**Checkpoint**: MVP complete — clean baseline install **and** working `implement-review`.

---

## Phase 5: US3 — No removed command survives as a hidden path (Priority: P2)

**Goal**: every remaining reference is history or false positive; no active wiring; no
silent redirect.

- [X] T026 [P] [US3] Delete runtime modules `src/speckit_powerpack/assets/runtime/powerpack_debt.py` and `src/speckit_powerpack/assets/runtime/powerpack_full_cycle.py`.
- [X] T027 [P] [US3] Delete config/policy/template assets `src/speckit_powerpack/assets/config/default-full-cycle.json`, `src/speckit_powerpack/assets/config/default-technical-debt.json`, `src/speckit_powerpack/assets/policies/technical-debt.md`, `src/speckit_powerpack/assets/templates/technical-debt-backlog.md` (remove now-empty dirs).
- [X] T028 [P] [US3] Delete dedicated tests `tests/test_debt_runtime.py`, `tests/test_full_cycle_runtime.py`.
- [X] T029 [US3] Edit `tests/test_assets_contract.py`: delete `test_debt_and_full_cycle_commands_are_packaged` and the full-cycle/debt assertions in other cases; keep/adjust the `speckit.implement-review.md` presence + no-`-v2` checks; ensure no assertion still expects a removed command file.
- [X] T030 [P] [US3] Delete exploratory homologation scaffolding: `scripts/homologation/probe_*.py`, repo-root `*.har` files, `docs/WEB_GITHUB_HEADLESS_PROBE.md`. For `tests/test_chatgpt_github_headless_probe_contract.py`: inspect its imports/subjects — if it only exercises a deleted `probe_*` module, delete it; if it also covers preserved `github_connector_preflight` / `github_browserless_smoke`, split or narrow it to the preserved surface instead of deleting (FR-021, analyze U1, CHK020–021).
- [X] T031 [P] [US3] Delete `docs/FULL_CYCLE.md` and `docs/TECHNICAL_DEBT.md`.
- [X] T032 [US3] Scrub current-state docs to present `implement-review` as the only current `powerpack-core` command: `README.md`, `docs/PROCESS_ARCHITECTURE.md`, `docs/CUSTOMIZATION.md`, `docs/DECISIONS_AND_TRADEOFFS.md`, `docs/INSTALLATION.md`, `docs/PORTABILITY.md`, `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`. Move any still-useful history into a dated, non-advertising note (FR-007, FR-008).
- [X] T033 [US3] Update cross-references in kept docs `docs/IMPLEMENT_REVIEW.md`, `docs/CHATGPT_GITHUB_BROWSERLESS_SMOKE.md`, `docs/CODEX_FIRST_INSTALL.md`, `docs/PROJECT_EVOLUTION.md` so none points to a deleted page or removed command as current.
- [X] T034 [US3] Run the repository-wide residual scan (quickstart §7 pattern: dotted removed names + `powerpack_debt` / `powerpack_full_cycle` / `technical-debt`) and produce `specs/001-single-skill-baseline/reference-classification.md` per `data-model.md` §Reference Classification; every hit `HISTORICAL_REFERENCE` or `FALSE_POSITIVE`, zero `ACTIVE_REFERENCE` (FR-016). Textual scan only — behavioural unknown-command proof is T035.
- [X] T035 [US3] Verify negative behavior **behaviourally** (FR-014 + FR-015): add an automated check (in `tests/test_baseline_contract.py` or the smoke) that, against a clean install, a removed command name (`speckit.implement`, `speckit.full-cycle`, a `speckit.debt-*`) is unknown at the registration/dispatch layer — not resolved, not redirected to `implement-review`. Textual absence (T034) is necessary but not sufficient.

**Checkpoint**: `reference-classification.md` shows 0 active references for every removed token.

---

## Phase 6: US4 — Baseline guarded against silent regression (Priority: P2)

**Goal**: adding a second `powerpack-core` command fails a test.

- [X] T036 [US4] Finalize `tests/test_baseline_contract.py` as the canonical exact-set guard: registration-side (parse `preset.yml`) + install-side (temp project), both equality assertions, plus a docstring pointing to FR-017 / spec §Regression Guard.
- [X] T037 [P] [US4] Add a guard-proof test note or CI check: adding a dummy second command entry to `preset.yml` makes `test_registration_command_set` fail (documented in the test module; do not commit the dummy entry).
- [X] T038 [P] [US4] Grep the whole `tests/` tree for any remaining membership-style assertion (`in ` against a command set / `.is_file()` for a command doc) that should be equality or is now obsolete; fix or delete (CHK024, CHK027).

**Checkpoint**: `pytest` green; regression guard demonstrably fails on a second command.

---

## Phase 7: Polish & Cross-Cutting

- [X] T039 [P] Run full `python -m pytest -q` — all green; confirm `test_debt_runtime.py` / `test_full_cycle_runtime.py` are gone and `test_baseline_contract.py` present (quickstart §1).
- [X] T040 [P] Quickstart walked: §1 (removed test files gone, `test_baseline_contract.py` present), §2 (registration exact-set), §3 (local `install_support` → only 3 runtimes, schema-2 prereqs, no residue), §4 (`install.sh`/`install.ps1` delegate to `install.py`), §5 (all 4 re-based-gate outcomes verified live in a temp installed project), §7 (0 active references), §8 (docs). Quickstart §3/§5 wording fixed for pre-merge / dev-repo. §4-on-Windows and §6 (full browserless flow) fold into T025.
- [X] T041 [P] Regenerate / verify `src/speckit_powerpack.egg-info/SOURCES.txt` via `python -m build` (build artifact — confirm it no longer lists deleted assets; do not hand-edit) (research.md §D7).
- [X] T042 [P] Update `README.md` top-of-file capability summary and any install snippet so a reader identifies the single current command in under 2 minutes (SC-007).
- [X] T043 [P] Add a dated entry to the changelog / `docs/PROJECT_EVOLUTION.md` recording the single-skill baseline as a scope decision (not a defect), linking spec 001 and PR #11 (FR-008).
- [X] T044 Update PR #11 description to reflect the completed cleanup (command set, re-based gate, deletions, `reference-classification.md` result).
- [X] T045 Constitution re-check note added to `plan.md` (§Post-Implementation Constitution Re-check — still a stub → PASS); `checklists/cleanup.md` items already 40/40 `[x]` from the reviewer-directed pass.

---

## Dependencies & Execution Order

- **Phase 1 (Setup)** → no deps. T002–T005 parallel.
- **Phase 2 (Foundational)** → needs Phase 1. T006→T007→T008 sequential (same file); T009 parallel to them (different file); T010–T013 parallel after T006–T008. **T018** (Phase 3, same file as T007) may be pulled forward to run immediately after T007 so the `implement begin/end` code and its tests (removed in T010) disappear together.
- **Phase 3 (US1)** → needs Phase 2 re-basing (T006–T009) done. T014→T020; T015/T017 parallel to T016/T018 (different files); T019 parallel.
- **Phase 4 (US2)** → needs Phase 3 (install path changed). T021/T022/T024 parallel; T023 after T007; T025 last in phase.
- **Phase 5 (US3)** → needs Phase 3 (preset no longer registers them) + Phase 2 re-basing (so deleting the wraps is safe). T026–T031 mostly parallel; T032/T033 sequential-ish (doc consistency); T034 after all deletions; T035 after T034.
- **Phase 6 (US4)** → needs Phase 3 + Phase 5. T036→T037/T038.
- **Phase 7 (Polish)** → needs Phases 3–6. T039 gates T040–T044.

## Parallel Execution Examples

- Phase 1: `T002`, `T003`, `T004`, `T005` together (all read-only, separate outputs).
- Phase 2: after `T008`, run `T010`, `T011`, `T012`, `T013` together (separate test files).
- Phase 5: `T026`, `T027`, `T028`, `T030`, `T031` together (independent deletions).
- Phase 7: `T039` then `T040`–`T043` together.

## Implementation Strategy

**MVP = Phase 1 + 2 + 3 + 4** (US1 + US2, both P1): a clean baseline that installs exactly
`implement-review` and a working re-based `implement-review` flow. Ship/verify here.

**Increment 2 = Phase 5** (US3): full deletion + zero active references.

**Increment 3 = Phase 6** (US4): regression guard locks the baseline.

**Increment 4 = Phase 7**: docs, changelog, PR, quickstart parity.

---

## Phase 8: Convergence

Assessed 2026-09-09 after `/speckit-implement`. One CRITICAL regression plus its
missing test coverage; everything else in the specified scope is satisfied.

- [X] T046 CRITICAL: Re-base the quality gate in `src/speckit_powerpack/assets/runtime/powerpack_capabilities.py` per FR-001 / FR-018 (contradicts). Its standalone `latest_implement_files()` (lines ~132-140) still reads `implement_runs` from feature state, which nothing populates after the wrap removal, so `capabilities.py gate detect` / `gate run` — the gate `speckit.implement-review.md` actually invokes — always sees `[]` and returns `NOT_APPLICABLE`. Give `capabilities.py` its own git-evidence `changed_paths(root)` helper mirroring `powerpack_runtime.changed_paths` (working tree via `git status --porcelain` + branch delta via `git diff <base> HEAD`, excluding `.specify/powerpack/`) and call it at the `main()` gate site instead of `latest_implement_files`; drop `latest_implement_files`.
- [X] T047 Add coverage for T046 in `tests/test_capabilities.py` per SC-003 / US2 (missing): a test that runs the `gate detect` path through `main()` (or the `changed_paths`-backed call site) in a temp git repo with a real code change and asserts the gate resolves to `REQUIRED`/`BLOCKED_CONFIGURATION` (architecture-dependent) rather than `NOT_APPLICABLE`, and with a docs-only change asserts `NOT_APPLICABLE`.

---

## Phase 9: PR #15 review remediation

Manual review of PR #15 against the SPEC-001 contract (2026-09-09). One HIGH functional
finding + two acceptance-verification notes.

- [X] T048 CRITICAL/HIGH: SPEC-scope the `implement-review` prerequisite evidence per FR-018a (contradicts / behavioral-regression). The first re-based gate accepted any non-doc change on the branch/worktree, so SPEC-B could be satisfied by SPEC-A's code — breaking "explicit same-SPEC predecessor is proven". Added `feature_base_commit(root, feature)` + `spec_implementation_delta(root, feature)` to `powerpack_runtime.py` (diff from the commit that introduced the SPEC's plan/tasks to HEAD; working tree not consulted; `NO_SPEC_BASELINE` when the SPEC's artifacts aren't committed). `implement_evidence`, `cmd_gate_detect/run`, `cmd_review_start` all use it; `powerpack_capabilities.py` mirrors it. `_branch_base` / whole-branch `changed_paths` removed from both runtimes.
- [X] T049 Cross-SPEC rejection test per FR-018a: `tests/test_powerpack_runtime.py::test_implement_evidence_rejects_other_specs_code_delta` (+ `_ignores_uncommitted_code`, `_no_spec_baseline_when_artifacts_uncommitted`); `test_capabilities.py::test_gate_main_uses_git_evidence_not_implement_runs` reworked for committed SPEC-scoped deltas. `pytest` = 94.
- [X] T050 Spec/plan/contract/docs updated for FR-018a: spec `## Clarifications` (PR #15 review) + FR-018a; `research.md §D1`; `contracts/implement-review-prereq.md`; `data-model.md`; `speckit.implement-review.md` "Mandatory predecessor"; `quickstart.md §5`; `T025-validation-runbook.md §S2`.
- [ ] T051 T025 acceptance test (full browserless `implement-review` flow) — the **live-service** portion only. Runbook: `T025-validation-runbook.md`. Reduced by `tests/test_implement_review_flow_survives_cleanup.py`: the flow's code path is proven to carry **zero references to removed commands/helpers** and the local plumbing (binding load, PR resolve, SPEC context, HEAD) runs, failing only at the Codex-auth boundary. What remains unverified here is solely that the live Codex/ChatGPT-Project/GitHub services respond — needs Codex login + a repo↔Project binding + a real PR.
- [X] T052 Windows `install.ps1` acceptance — CI matrix (`ubuntu/windows/macos × py 3.11/3.13`) **green** on PR #15 run 34420467199 after the draft was marked ready; includes `test_shell_wrappers_delegate_to_python_installer` and all installer tests on windows-latest.
