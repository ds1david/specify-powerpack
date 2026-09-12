# Implementation Plan: Single Skill Baseline

**Branch**: `001-single-skill-baseline` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-single-skill-baseline/spec.md`

## Summary

Reduce Specify PowerPack so the `powerpack-core` preset exposes exactly one command,
`speckit.implement-review`. Every other preset command (`speckit.implement`,
`speckit.converge`, `speckit.checklist-converge`, `speckit.full-cycle`, and the five
`speckit.debt-*` commands) is removed together with its runtime, config, docs, tests and
installer wiring. The `implement-review` flow is re-based off the removed
`speckit.implement` / `speckit.converge` wraps onto upstream Spec Kit `speckit-implement` /
`speckit-converge`, and its prerequisite gate is re-based from a PowerPack `implement` state
receipt onto **repository evidence** (`tasks.md` fully checked + a non-documentation
implementation delta). The `powerpack-tools` extension (`doctor`, `update`) and the generic
`powerpack.py` runtime surface are preserved as infrastructure. Smoke/contract tests are
tightened from "command file present" to exact-set equality over the `powerpack-core`
`provides.templates` names, and a regression guard encodes `{"speckit.implement-review"}` as
the baseline contract.

## Technical Context

**Language/Version**: Python ≥ 3.11 (`pyproject.toml` `requires-python`); tested on
3.12 / 3.13. Installed runtime (`.specify/powerpack/bin/*.py`) is **stdlib-only by design** —
no third-party imports.

**Primary Dependencies**: None at runtime. Dev: `pytest>=8,<9`, `build>=1.2,<2`. Spec Kit
(`specify` CLI) ≥ 1.0.0 is a peer tool, not a Python dependency.

**Storage**: Files only. PowerPack state lives under `.specify/powerpack/` in the target
project (JSON receipts); preset/extension assets are packaged under
`src/speckit_powerpack/assets/` and copied at install time.

**Testing**: `pytest` (`tests/`, `pythonpath = ["src"]`). Asset/installer contract tests
(`test_assets_contract.py`, `test_installer.py`, `test_install_support.py`), runtime tests,
and a new baseline-contract test. Homologation smoke: `scripts/homologation/` +
`tests/e2e/`.

**Target Platform**: Cross-platform CLI. Officially supported install entrypoints:
`install.sh` (Linux/WSL/macOS), `install.py` (any Python platform), `install.ps1`
(Windows PowerShell). One canonical integration (`codex`, the `DEFAULT_INTEGRATION`) for
the parity gate.

**Project Type**: Single project — Python packaging/CLI + bundled asset tree (preset
commands, extension, stdlib runtime).

**Performance Goals**: N/A (developer tooling; install completes in seconds).

**Constraints**: Runtime stays stdlib-only. No compatibility shims / aliases / hidden copies
for removed commands (FR-014). `implement-review` behavior must not change except the
re-basing required by removals (FR-001, FR-018). Historical references may remain only as
non-advertising history (FR-008).

**Scale/Scope**: ~10 preset command docs, 3 runtime modules, ~6 config/policy/template
assets, ~4 docs, ~3 dedicated test modules, `cli.py` install wiring, `preset.yml`. Net a
deletion-dominant change plus one focused re-basing of the `implement-review` prereq.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the **unpopulated template** (all `[PLACEHOLDER]`
tokens, no ratified principles). There are therefore no constitutional gates to evaluate.

Provisional alignment with the template's example principles, for the record:

| Example principle | This feature |
|---|---|
| Library-First / Simplicity (YAGNI) | Directly advances it — removes unproven surface. PASS |
| CLI Interface (text I/O) | Unchanged; `powerpack.py` stays stdlib CLI. PASS |
| Test-First | New exact-set contract test + re-based-gate tests written before deletion; removed-command tests deleted with their code. PASS |
| Integration Testing (contract changes) | Installer/preset contract is exactly what changes; covered by `contracts/` + quickstart. PASS |
| Versioning / Breaking Changes | Intentionally breaking for removed-command consumers; no shim (FR-014). Recorded in Migration Strategy. PASS |

**Result: PASS (no ratified constitution; no violations).** Re-check after Phase 1: still
PASS — design adds no new projects, patterns, or runtime dependencies.

## Project Structure

### Documentation (this feature)

```text
specs/001-single-skill-baseline/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions (gate re-basing, removal inventory, enumeration rule)
├── data-model.md        # Phase 1 — inventory record, reference classification, exact-set contract entities
├── quickstart.md        # Phase 1 — validation scenarios (clean install, exact-set, re-based gate, parity)
├── contracts/
│   ├── command-inventory.md        # How the powerpack-core command set is enumerated (both sides)
│   ├── implement-review-prereq.md  # Re-based prerequisite gate contract
│   └── installer-parity.md         # Post-install state contract for the 3 entrypoints
├── checklists/
│   └── requirements.md  # Spec-quality checklist (already created)
└── tasks.md             # Phase 2 — /speckit-tasks (NOT created here)
```

### Source Code (repository root)

> The per-file DELETE/EDIT/KEEP annotations below are a planning view. The **authoritative
> removal inventory** is `research.md §D7` — if the two ever diverge, §D7 wins and this
> tree is updated to match.

```text
src/speckit_powerpack/
├── cli.py                          # EDIT: install_support() — drop removed runtime/config/policy copies;
│                                   #       rewrite prerequisites.json default (remove checklist-converge;
│                                   #       re-base implement-review step to evidence check)
├── assets/
│   ├── presets/powerpack-core/
│   │   ├── preset.yml              # EDIT: provides.templates → only speckit.implement-review
│   │   └── commands/
│   │       ├── speckit.implement-review.md   # EDIT: re-base prose onto upstream speckit-implement /
│   │       │                                 #       speckit-converge; drop "return to speckit-implement"
│   │       │                                 #       wording that names the removed wrap
│   │       ├── speckit.implement.md          # DELETE
│   │       ├── speckit.converge.md           # DELETE
│   │       ├── speckit.checklist-converge.md # DELETE
│   │       ├── speckit.full-cycle.md         # DELETE
│   │       └── speckit.debt-*.md (×5)        # DELETE
│   ├── runtime/
│   │   ├── powerpack_runtime.py    # EDIT: remove `implement begin/end` subcommands and the
│   │   │                           #       implement/converge `state mark` paths that only served the
│   │   │                           #       wraps; add evidence-based implement-review prereq evaluator;
│   │   │                           #       drop checklist-converge from default_prerequisites()
│   │   ├── powerpack_capabilities.py     # KEEP (implement-review quality gate)
│   │   ├── powerpack_review_protocol.py  # KEEP (implement-review deep review)
│   │   ├── powerpack_debt.py             # DELETE
│   │   └── powerpack_full_cycle.py       # DELETE
│   ├── config/
│   │   ├── default-model-routing.json    # EDIT: keep only implement-review (+ generic stages still
│   │   │                                 #       used by the runtime); drop implement/converge/
│   │   │                                 #       checklist-converge/full-cycle/debt-*/powerpack-update
│   │   ├── default-review.json           # KEEP
│   │   ├── default-update.json           # KEEP (powerpack-tools/update)
│   │   ├── default-full-cycle.json       # DELETE
│   │   └── default-technical-debt.json   # DELETE
│   ├── policies/technical-debt.md        # DELETE
│   ├── templates/technical-debt-backlog.md   # DELETE
│   ├── review/deep-review-protocol.md    # KEEP (implement-review)
│   └── extensions/powerpack-tools/       # KEEP intact (doctor, update) — trim only removed-command
│                                         # references inside update.md if any
└── github_browserless_smoke.py, github_connector_preflight.py, browserless_review.py,
    chatgpt_project_provider.py, codex_apps*, capabilities/review modules   # KEEP (implement-review)

tests/
├── test_assets_contract.py         # EDIT: replace presence checks with exact-set equality;
│                                   #       DELETE test_debt_and_full_cycle_commands_are_packaged and
│                                   #       full-cycle/debt assertions; add baseline-contract test
├── test_baseline_contract.py       # NEW: assert powerpack-core provides.templates == {implement-review}
│                                   #      at asset level AND after a clean install into a tmp project
├── test_install_support.py         # EDIT: drop removed copies; assert none of the removed assets land
├── test_installer.py               # EDIT: post-install command set == {implement-review}
├── test_powerpack_runtime.py       # EDIT: re-based implement-review prereq evidence cases;
│                                   #       remove implement begin/end cases
├── test_full_cycle_runtime.py      # DELETE
├── test_debt_runtime.py            # DELETE
└── e2e/ + scripts/homologation/    # EDIT: keep smoke_chatgpt_github_browserless.py; DELETE probe_*.py
                                    # and *.har; ensure smoke asserts exact-set

docs/
├── README.md, PROCESS_ARCHITECTURE.md, AGENTS.md, CLAUDE.md, .claude/CLAUDE.md,
│   CUSTOMIZATION.md, DECISIONS_AND_TRADEOFFS.md, INSTALLATION.md, PORTABILITY.md
│                                   # EDIT: present implement-review as the only current command
├── IMPLEMENT_REVIEW.md, CHATGPT_GITHUB_BROWSERLESS_SMOKE.md   # KEEP (update cross-refs)
├── FULL_CYCLE.md, TECHNICAL_DEBT.md # DELETE (or convert to dated history under a "historical" note)
└── WEB_GITHUB_HEADLESS_PROBE.md     # DELETE (exploratory scaffolding, FR-021)

install.sh / install.py / install.ps1  # VERIFY: no removed-command wiring; each yields {implement-review}
*.har (repo root)                       # DELETE (FR-021; also now .gitignored)
```

**Structure Decision**: Single-project layout is unchanged. All work is deletion + a
focused re-basing inside `cli.py` + `powerpack_runtime.py` + `speckit.implement-review.md`,
plus test tightening. No new package, module boundary, or dependency is introduced.

## Phase 0 — Research

See [research.md](./research.md). Decisions resolved:

1. **`implement-review` prerequisite re-basing** — evidence-based gate (`tasks.md` all
   `[X]` + non-documentation implementation delta), replacing the PowerPack `implement`
   state receipt. Upstream `speckit-implement` emits no PowerPack receipt, so the gate reads
   repo state directly using primitives already in `powerpack_runtime.py`.
2. **`implement-review` convergence re-basing** — Phase 1 prose calls upstream
   `speckit-converge` / `speckit-implement` by their exact upstream names; the
   `speckit.converge` `state mark converge` receipt is dropped (it fed nothing that
   survives).
3. **Command-set enumeration rule** — authoritative source is the `provides.templates`
   `name:` list in `preset.yml`; tests parse that, not filenames.
4. **`powerpack-tools` scope** — preserved as infrastructure; exact-set assertion is scoped
   to `powerpack-core` only.
5. **Installer parity** — validate `install.sh` / `install.py` / `install.ps1` against one
   canonical integration; cross-integration parity by inspection.
6. **Documentation strategy** — delete command-dedicated pages; convert genuinely useful
   history to dated, non-advertising notes; scrub current-state docs.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — Command Inventory Record, Reference Classification,
  Exact-Set Baseline Contract, Re-based Prerequisite Evidence.
- [contracts/command-inventory.md](./contracts/command-inventory.md) — enumeration rule and
  the equality assertion for both registration-time and install-time.
- [contracts/implement-review-prereq.md](./contracts/implement-review-prereq.md) — inputs,
  pass/fail conditions, and JSON output shape of the re-based gate.
- [contracts/browserless-review-evidence.md](./contracts/browserless-review-evidence.md) —
  structured attachments, connector binding, pacing, evidence retention and external blocks.
- [contracts/installer-parity.md](./contracts/installer-parity.md) — the post-install file
  and command-set state every entrypoint must produce.
- [quickstart.md](./quickstart.md) — runnable validation scenarios.

**Post-Design Constitution Re-check: PASS** — no new projects/patterns/dependencies; change
reduces surface area.

## Post-Checklist Refinement

`checklists/cleanup.md` (40 requirements-quality items, CHK001–CHK040) is the reviewer gate
for this feature. Review of those items against the spec/plan produced two spec updates:

1. Added an explicit Assumption that every target has upstream `speckit-implement` /
   `speckit-converge` (the re-based gate depends on it — CHK038).
2. Confirmed the baseline-SHA discrepancy is already handled by the Assumptions section
   (CHK039) and the `default-model-routing.json` generic-stage classification (CHK007) is
   correctly deferred to `/speckit-tasks` as a named verification (research.md §D7).

No plan restructuring required; the remaining unchecked checklist items are reviewer
judgment calls, not missing plan content.

## Post-Analyze Remediation (`/speckit-analyze`, 2026-09-09)

Cross-artifact analysis found 0 CRITICAL, 10 findings. Applied:

| Finding | Fix |
|---|---|
| C1 (HIGH) — FR-014 had no verification task | spec FR-14 now mandates a *behavioural* unknown-command check; tasks T034/T035 scope widened |
| I1 (MED) — FR-020/021 outside `### Functional Requirements` | folded into the FR list as FR-020/FR-021/FR-022 |
| U1 (MED) — probe-test deletion criterion vague | spec FR-021 + task T030 now say: split/narrow a mixed test, delete only probe-only tests |
| D1 (MED) — `state mark`/`state check` possibly dead after cleanup | task T018 gets a sub-check for a surviving consumer |
| A1 (MED) — SC-007 subjective | reworded to an inspection-verifiable criterion |
| S1 (LOW) — Python version wording | corrected to "≥3.11, tested 3.12/3.13" |
| Q1 (LOW) — FR-003/FR-012 overlap | FR-012 narrowed to flags/keys/routing; whole files → FR-003 |
| Q2 (LOW) — inventory duplicated | this plan's tree now defers to `research.md §D7` as source of truth |
| I2 (LOW) — T010 removes tests before T018 removes code | Dependencies note: T018 may run right after T007 |
| M1 (LOW) — process tasks unmapped | accepted as cross-cutting; no change |

## Complexity Tracking

No constitution violations. No entries required.

## Post-Implementation Constitution Re-check (2026-09-09)

`.specify/memory/constitution.md` is still the unpopulated template — no ratified
principles, no gates. **Final result: PASS.** The delivered change adds no new project,
module boundary, runtime dependency, or pattern; it is deletion-dominant plus one focused
re-basing of the `implement-review` prerequisite/gate onto git evidence (both `powerpack.py`
and `capabilities.py`, per Phase 8). If the constitution is later populated, re-run this
check against the merged tree.

Reviewer gate `checklists/cleanup.md`: 40/40 evaluated and `[x]` (reviewer-directed pass,
2026-09-09). CHK007 and CHK036 accepted with recorded rationale.

## Review Execution Package Addendum (2026-09-11)

The preserved browserless review is an evidence-first workflow, not a large prompt containing
all state. It uses one compact execution command and an attached Review Evidence Package with
the output schema, master orchestrator, packet, protocol, GitHub evidence contract, SPEC
artifacts, previous findings and instructions. The package manifest is the traceability
boundary; its files are copied into `T025-evidence/<run>-attachments/` and uploaded as native
conversation attachments.

Execution phases are input validation, immutable snapshot resolution, evidence acquisition,
SPEC review, adversarial challenge and final serialization. A GitHub connector call is
mandatory before repository interpretation. Connector identity is resolved for the active
ChatGPT account and authorization is JIT; no GitHub token or stale connector id is part of the
contract. If required evidence is unavailable, the state is `PENDING_EXTERNAL_REVIEW` and
implementation acceptance tasks remain open.

All attachment, processing, authorization, retry and submission boundaries use one injectable
random 1.5–4.0 second wait policy. There is no fixed two-second polling loop. These decisions
are captured by FR-023–FR-030 and SC-008–SC-012; live external validation remains separate from
the FR-018a implementation gate.
