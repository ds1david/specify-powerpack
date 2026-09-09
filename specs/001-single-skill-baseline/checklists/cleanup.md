# Scope-Reduction Requirements Checklist: Single Skill Baseline

**Purpose**: Validate that the requirements for removing every `powerpack-core` command
except `implement-review` are complete, unambiguous, measurable, and internally consistent —
before implementation. "Unit tests for the English", not for the code.
**Created**: 2026-09-09
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Review Ownership**: Reviewer-owned requirements-quality artifact. `[x]` means the reviewer
judged the requirement-quality criterion satisfied — it does NOT mean implementation is done.
`/speckit-implement` reads checkbox state as a gate and must not modify markers.

## Removal Scope Definition

- [ ] CHK001 Is the unit of removal ("PowerPack-provided command" = `powerpack-core` `provides.templates` entry) defined precisely enough that a reader can list every in-scope item without guessing? [Clarity, Spec §Terminology]
- [ ] CHK002 Are the exact commands to remove enumerated by name, and does that list match the baseline `preset.yml` at SHA `489f5355`? [Completeness, Spec §Terminology / research.md §D7]
- [ ] CHK003 Is "removed" defined as an explicit set of artifact classes (command file, runtime, config, policy, template, docs, tests, installer wiring) rather than left open-ended? [Completeness, Spec §FR-003]
- [ ] CHK004 Are the out-of-scope sets (upstream `speckit-*` skills; `powerpack-tools` extension) stated as hard exclusions the implementation may not touch? [Clarity, Spec §Terminology / §FR-013]
- [ ] CHK005 Is there a requirement that the removal set be derived from the real repository/preset inventory, not only from a hand-maintained name list? [Completeness, Spec §FR-002]
- [ ] CHK006 Does the spec require a per-command `PRESERVE`/`REMOVE` decision record produced *before* deletion, with defined fields? [Completeness, Spec §FR-002 / data-model.md]
- [ ] CHK007 Is the boundary between "command-specific config" and "shared core config" defined well enough to classify each key in `default-model-routing.json`? [Ambiguity, Spec §FR-012 / research.md §D7]

## Preserved Capability & Shared Dependencies

- [ ] CHK008 Is "preserve `implement-review` behavior unchanged except where a removed dependency forces a change" stated with enough precision to tell an allowed change from a regression? [Clarity, Spec §FR-001]
- [ ] CHK009 Are the assets that `implement-review` depends on (deep-review protocol, capabilities runtime, review-protocol runtime, browserless review modules, `doctor`) explicitly listed as KEEP? [Completeness, plan.md §Project Structure / research.md §D7]
- [ ] CHK010 Is there a requirement to prove (not assume) that no preserved module imports `powerpack_debt` or `powerpack_full_cycle` before deletion? [Coverage, Gap / research.md §D7 open-verification]
- [ ] CHK011 Are the generic `powerpack.py` subcommands that must survive (`state`, `review`, `limit`, `gate`, `model`) distinguished from the wrap-only ones to be removed (`implement begin/end`)? [Clarity, plan.md §Project Structure]
- [ ] CHK012 Does the spec require that removing a shared helper is forbidden when `implement-review` / install lifecycle / core still needs it? [Consistency, Spec §FR-013 / §R-003]

## Re-based `implement-review` Prerequisite Gate (FR-018)

- [ ] CHK013 Is the replacement prerequisite mechanism named concretely (repository-evidence: `tasks.md` all `[X]` + non-doc implementation delta) rather than described only as "re-base onto upstream"? [Clarity, Spec §FR-018 / contracts/implement-review-prereq.md]
- [ ] CHK014 Are the pass/fail conditions of the re-based gate individually testable, each with a named failure reason (`MISSING_TASKS` / `TASKS_INCOMPLETE` / `NO_IMPLEMENTATION_DELTA`)? [Measurability, contracts/implement-review-prereq.md]
- [ ] CHK015 Is the offline / non-git behavior of the gate specified (degrade to tasks-only, annotate) so it does not hard-block CI? [Edge Case, contracts/implement-review-prereq.md]
- [ ] CHK016 Is the original intent the gate protects ("`implement-review` never satisfies its own predecessor; a real prior implementation must exist") preserved in the new wording? [Consistency, Spec §FR-018 vs §User Story 2]
- [ ] CHK017 Are the `prerequisites.json` shape change and backward-compat handling of a legacy `{"step":"implement","statuses":["COMPLETED"]}` entry specified? [Completeness, contracts/implement-review-prereq.md §Config]
- [ ] CHK018 Is it explicit that the Phase 1 convergence loop must call upstream `speckit-converge` / `speckit-implement` (hyphenated) and never the removed dotted wraps? [Clarity, research.md §D2 / Spec §Assumptions]
- [ ] CHK019 Is there a requirement to rewrite the `implement-review.md` prose that currently says "return to `speckit-implement`" / "run `speckit-implement`" so it cannot be read as referencing the removed `speckit.implement` wrap? [Ambiguity, Spec §FR-016 follow-through / research.md §D2]

## Browserless Review Path Scope (FR-020 / FR-021)

- [ ] CHK020 Is the boundary between "preserved browserless review contract" and "removed exploratory scaffolding" drawn by explicit path patterns (`smoke_chatgpt_github_browserless.py` kept; `probe_*`, `*.har`, `WEB_GITHUB_HEADLESS_PROBE.md` removed)? [Clarity, Spec §FR-020 / §FR-021]
- [ ] CHK021 Is there a requirement covering tests tied to removed probes (delete) versus tests covering the preserved smoke/connector-preflight (keep)? [Completeness, Spec §FR-021 / §FR-009]
- [ ] CHK022 Are `full-cycle` and technical-debt docs/scripts explicitly routed to the normal removed-command rule rather than left ambiguous alongside the browserless carve-out? [Consistency, Spec §Browserless review path]

## Exact-Set Contract & Regression Guard

- [ ] CHK023 Is the enumeration source for "PowerPack-provided command" singular and named (`preset.yml` `provides.templates[].name`), so the equality assertion has one definition? [Clarity, contracts/command-inventory.md]
- [ ] CHK024 Does the spec require set **equality** (not membership) at both registration time and install time, with the insufficient `"x" in set` form explicitly rejected? [Measurability, Spec §FR-011]
- [ ] CHK025 Is "no residual removed-command artifact" defined as a checkable list of file names/paths rather than a vague absence claim? [Measurability, contracts/installer-parity.md §7 / quickstart.md §3]
- [ ] CHK026 Is the regression-guard requirement specific about what must fail (adding any second `powerpack-core` command) and where the contract lives? [Clarity, Spec §FR-017 / §Regression Guard]
- [ ] CHK027 Are the existing presence-style assertions that must be inverted/deleted identified (e.g. `test_debt_and_full_cycle_commands_are_packaged`)? [Completeness, research.md §D3 / plan.md]

## Installer Parity

- [ ] CHK028 Are the officially supported install entrypoints enumerated exactly (`install.sh`, `install.py`, `install.ps1`) with the canonical integration named? [Clarity, Spec §FR-005 / §Clarifications]
- [ ] CHK029 Is the post-install invariant expressed as concrete present/absent file lists and config-content assertions, not "installs correctly"? [Measurability, contracts/installer-parity.md]
- [ ] CHK030 Is the decision to assume `codex` vs `claude` integration parity by inspection (not e2e) stated as an explicit, justified scope limit? [Assumption, Spec §FR-019 / research.md §D5]
- [ ] CHK031 Are idempotent re-run and `--reset-config` behaviors covered by requirements for the new baseline shape? [Coverage, contracts/installer-parity.md §Re-run]

## Repository Verification & History

- [ ] CHK032 Is the reference-classification scheme (`ACTIVE_REFERENCE` / `HISTORICAL_REFERENCE` / `FALSE_POSITIVE`) defined with the acceptance rule `ACTIVE_REFERENCE == 0` per removed token? [Clarity, Spec §Repository Verification]
- [ ] CHK033 Does the spec define which contexts make a `HISTORICAL_REFERENCE` acceptable (changelog / completed spec / ADR / merged PR) versus advertising current support? [Ambiguity, Spec §FR-008]
- [ ] CHK034 Is the residual-scan search pattern specified to match the dotted removed names and `powerpack_debt` / `powerpack_full_cycle` / `technical-debt` tokens, not the hyphenated upstream names? [Coverage, quickstart.md §7 / research.md §D2]

## Success Criteria Quality

- [ ] CHK035 Are all Success Criteria (SC-001..007) objectively verifiable without knowing implementation internals? [Measurability, Spec §Success Criteria]
- [ ] CHK036 Is SC-003 ("no failure attributable to a removed command") worded so a reviewer can decide attribution unambiguously? [Clarity, Spec §SC-003]
- [ ] CHK037 Does SC-007's "under 2 minutes from the README" have a defined evaluation method (who, what task)? [Measurability, Spec §SC-007]

## Dependencies, Assumptions & Conflicts

- [ ] CHK038 Is the assumption that upstream `speckit-converge` / `speckit-implement` exist and are installed in every target validated, not just asserted? [Assumption, research.md §D2]
- [ ] CHK039 Is the baseline SHA discrepancy (`a825557` in the old draft vs current HEAD `489f5355`) resolved with a requirement to record the actual starting SHA and explain inventory deltas? [Conflict, Spec §Assumptions / §Repository Baseline]
- [ ] CHK040 Are the "open verification" items in research.md §D7 (model-routing generic stages still consumed; `egg-info` regenerates) tracked as requirements for `/speckit-tasks` rather than left as loose notes? [Gap, research.md §D7]

## Notes

- Focus areas (auto-selected, empty user input): removal scope & completeness; re-based
  `implement-review` gate; exact-set contract measurability; installer parity; repository
  verification. Depth: standard. Audience: PR reviewer.
- ≥80% of items carry a `[Spec §…]` / `contracts/…` / `research.md §…` reference or a
  `[Gap]` / `[Ambiguity]` / `[Conflict]` / `[Assumption]` marker.
- Unchecked items are open requirements-quality questions to resolve (via spec edits or
  `/speckit-clarify`) before or during `/speckit-tasks`.
