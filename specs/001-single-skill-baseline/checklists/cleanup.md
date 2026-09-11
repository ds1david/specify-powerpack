# Scope-Reduction Requirements Checklist: Single Skill Baseline

**Purpose**: Validate that the requirements for removing every `powerpack-core` command
except `implement-review` are complete, unambiguous, measurable, and internally consistent —
before implementation. "Unit tests for the English", not for the code.
**Created**: 2026-09-09
**Reviewed**: 2026-09-09 (reviewer-directed evaluation; see Notes)
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Review Ownership**: Reviewer-owned requirements-quality artifact. `[x]` means the reviewer
judged the requirement-quality criterion satisfied — it does NOT mean implementation is done.
`/speckit-implement` reads checkbox state as a gate and must not modify markers.

## Removal Scope Definition

- [x] CHK001 Is the unit of removal ("PowerPack-provided command" = `powerpack-core` `provides.templates` entry) defined precisely enough that a reader can list every in-scope item without guessing? [Clarity, Spec §Terminology]
- [x] CHK002 Are the exact commands to remove enumerated by name, and does that list match the baseline `preset.yml` at SHA `489f5355`? [Completeness, Spec §Terminology / research.md §D7]
- [x] CHK003 Is "removed" defined as an explicit set of artifact classes (command file, runtime, config, policy, template, docs, tests, installer wiring) rather than left open-ended? [Completeness, Spec §FR-003]
- [x] CHK004 Are the out-of-scope sets (upstream `speckit-*` skills; `powerpack-tools` extension) stated as hard exclusions the implementation may not touch? [Clarity, Spec §Terminology / §FR-013]
- [x] CHK005 Is there a requirement that the removal set be derived from the real repository/preset inventory, not only from a hand-maintained name list? [Completeness, Spec §FR-002]
- [x] CHK006 Does the spec require a per-command `PRESERVE`/`REMOVE` decision record produced *before* deletion, with defined fields? [Completeness, Spec §FR-002 / data-model.md]
- [x] CHK007 Is the boundary between "command-specific config" and "shared core config" defined well enough to classify each key in `default-model-routing.json`? [Ambiguity, Spec §FR-012 / research.md §D3 config-key rule / §D7]

## Preserved Capability & Shared Dependencies

- [x] CHK008 Is "preserve `implement-review` behavior unchanged except where a removed dependency forces a change" stated with enough precision to tell an allowed change from a regression? [Clarity, Spec §FR-001 / §FR-018]
- [x] CHK009 Are the assets that `implement-review` depends on (deep-review protocol, capabilities runtime, review-protocol runtime, browserless review modules, `doctor`) explicitly listed as KEEP? [Completeness, plan.md §Project Structure / research.md §D7]
- [x] CHK010 Is there a requirement to prove (not assume) that no preserved module imports `powerpack_debt` or `powerpack_full_cycle` before deletion? [Coverage, research.md §D7 / tasks.md T003]
- [x] CHK011 Are the generic `powerpack.py` subcommands that must survive distinguished from the wrap-only ones to be removed (`implement begin/end`), with a check for now-orphaned `state mark`/`state check`? [Clarity, plan.md §Project Structure / tasks.md T018]
- [x] CHK012 Does the spec require that removing a shared helper is forbidden when `implement-review` / install lifecycle / core still needs it? [Consistency, Spec §FR-013 / §R-003]

## Re-based `implement-review` Prerequisite Gate (FR-018)

- [x] CHK013 Is the replacement prerequisite mechanism named concretely (repository-evidence: `tasks.md` all `[X]` + non-doc implementation delta) rather than described only as "re-base onto upstream"? [Clarity, Spec §FR-018 / contracts/implement-review-prereq.md]
- [x] CHK014 Are the pass/fail conditions of the re-based gate individually testable, each with a named failure reason (`MISSING_TASKS` / `TASKS_INCOMPLETE` / `NO_IMPLEMENTATION_DELTA`)? [Measurability, contracts/implement-review-prereq.md]
- [x] CHK015 Is the offline / non-git behavior of the gate specified (degrade to tasks-only, annotate) so it does not hard-block CI? [Edge Case, contracts/implement-review-prereq.md]
- [x] CHK016 Is the original intent the gate protects ("`implement-review` never satisfies its own predecessor; a real prior implementation must exist") preserved in the new wording? [Consistency, Spec §FR-018 vs §User Story 2 / research.md §D1]
- [x] CHK017 Are the `prerequisites.json` shape change and backward-compat handling of a legacy `{"step":"implement","statuses":["COMPLETED"]}` entry specified? [Completeness, contracts/implement-review-prereq.md §Config]
- [x] CHK018 Is it explicit that the Phase 1 convergence loop must call upstream `speckit-converge` / `speckit-implement` (hyphenated) and never the removed dotted wraps? [Clarity, research.md §D2 / Spec §Assumptions]
- [x] CHK019 Is there a requirement to rewrite the `implement-review.md` prose that currently names `speckit-implement` so it cannot be read as referencing the removed `speckit.implement` wrap? [Ambiguity, research.md §D2 / tasks.md T009]

## Browserless Review Path Scope (FR-020 / FR-021 / FR-022)

- [x] CHK020 Is the boundary between "preserved browserless review contract" and "removed exploratory scaffolding" drawn by explicit path patterns (`smoke_chatgpt_github_browserless.py` kept; `probe_*`, `*.har`, `WEB_GITHUB_HEADLESS_PROBE.md` removed)? [Clarity, Spec §FR-020 / §FR-021]
- [x] CHK021 Is there a requirement covering tests tied to removed probes (delete) versus tests covering the preserved smoke/connector-preflight (keep or split)? [Completeness, Spec §FR-021 / §FR-009]
- [x] CHK022 Are `full-cycle` and technical-debt docs/scripts explicitly routed to the normal removed-command rule rather than left ambiguous alongside the browserless carve-out? [Consistency, Spec §FR-022]

## Exact-Set Contract & Regression Guard

- [x] CHK023 Is the enumeration source for "PowerPack-provided command" singular and named (`preset.yml` `provides.templates[].name`), so the equality assertion has one definition? [Clarity, contracts/command-inventory.md / research.md §D3]
- [x] CHK024 Does the spec require set **equality** (not membership) at both registration time and install time, with the insufficient `"x" in set` form explicitly rejected? [Measurability, Spec §FR-011]
- [x] CHK025 Is "no residual removed-command artifact" defined as a checkable list of file names/paths rather than a vague absence claim? [Measurability, contracts/installer-parity.md §7 / quickstart.md §3]
- [x] CHK026 Is the regression-guard requirement specific about what must fail (adding any second `powerpack-core` command) and where the contract lives? [Clarity, Spec §FR-017 / §Regression Guard]
- [x] CHK027 Are the existing presence-style assertions that must be inverted/deleted identified (e.g. `test_debt_and_full_cycle_commands_are_packaged`)? [Completeness, research.md §D3 / tasks.md T029]

## Installer Parity

- [x] CHK028 Are the officially supported install entrypoints enumerated exactly (`install.sh`, `install.py`, `install.ps1`) with the canonical integration named (`codex`)? [Clarity, Spec §FR-005 / §FR-019]
- [x] CHK029 Is the post-install invariant expressed as concrete present/absent file lists and config-content assertions, not "installs correctly"? [Measurability, contracts/installer-parity.md]
- [x] CHK030 Is the decision to assume `codex` vs `claude` integration parity by inspection (not e2e) stated as an explicit, justified scope limit? [Assumption, Spec §FR-019 / research.md §D5]
- [x] CHK031 Are idempotent re-run and `--reset-config` behaviors covered by requirements for the new baseline shape? [Coverage, contracts/installer-parity.md §Re-run]

## Repository Verification & History

- [x] CHK032 Is the reference-classification scheme (`ACTIVE_REFERENCE` / `HISTORICAL_REFERENCE` / `FALSE_POSITIVE`) defined with the acceptance rule `ACTIVE_REFERENCE == 0` per removed token? [Clarity, Spec §Repository Verification]
- [x] CHK033 Does the spec define which contexts make a `HISTORICAL_REFERENCE` acceptable (changelog / completed spec / ADR / merged PR) versus advertising current support? [Ambiguity, Spec §FR-008 / §Repository Verification]
- [x] CHK034 Is the residual-scan search pattern specified to match the dotted removed names and `powerpack_debt` / `powerpack_full_cycle` / `technical-debt` tokens, not the hyphenated upstream names? [Coverage, quickstart.md §7 / research.md §D2]

## Success Criteria Quality

- [x] CHK035 Are all Success Criteria (SC-001..007) objectively verifiable without knowing implementation internals? [Measurability, Spec §Success Criteria]
- [x] CHK036 Is SC-003 ("no failure attributable to a removed command") worded so a reviewer can decide attribution unambiguously? [Clarity, Spec §SC-003 — attribution now defined via revert/bisect]
- [x] CHK037 Is SC-007 measurable by a defined evaluation method? [Measurability, Spec §SC-007 — reworded to "README section names exactly one command", inspection-verifiable]

## Dependencies, Assumptions & Conflicts

- [x] CHK038 Is the assumption that upstream `speckit-converge` / `speckit-implement` exist and are installed in every target validated, not just asserted? [Assumption, Spec §Assumptions / tasks.md T005]
- [x] CHK039 Is the baseline SHA discrepancy (`a825557` vs current HEAD `489f5355`) resolved with a requirement to record the actual starting SHA and explain inventory deltas? [Conflict, Spec §Assumptions / tasks.md T001]
- [x] CHK040 Are the "open verification" items in research.md §D7 (model-routing generic stages still consumed; `egg-info` regenerates) tracked as tasks rather than loose notes? [Gap, tasks.md T004 / T041]

## Notes

- **Reviewed 2026-09-09** at the reviewer's direction. All 40 items evaluated against the
  current `spec.md` / `plan.md` / `tasks.md` / `research.md` / `contracts/`. Every item is
  satisfied; gaps found during the `/speckit-analyze` remediation and this review were fixed
  in the artifacts (config-key classification rule in research.md §D3, SC-003 attribution
  definition, SC-007 rewording, FR-019 names `codex`, FR-021/FR-022 test-split rule,
  T018 orphan-subcommand check).
- Borderline items accepted with rationale: **CHK007** (boundary is now a mechanical
  grep-backed rule, not judgement); **CHK036** (attribution now defined by revert/bisect,
  still requires reviewer sign-off at implementation time).
- Focus areas (auto-selected, empty user input): removal scope & completeness; re-based
  `implement-review` gate; exact-set contract measurability; installer parity; repository
  verification. Depth: standard. Audience: PR reviewer.
- `/speckit-implement` reads checkbox state as a gate: all items `[x]` ⇒ PASS, no prompt.
  `[x]` here means "requirements quality approved", NOT "implementation complete".

## Review Evidence Package Addendum

- [ ] CHK041 Is the compact execution prompt separated from the attached Review Evidence
  Package, with explicit authority for schema, packet, evidence contract, protocol, SPEC and
  lifecycle artifacts? [Consistency, Spec §FR-023/FR-030]
- [ ] CHK042 Does the package contract require every attachment to finish processing before
  native attachment metadata is submitted, including a manifest with digests? [Completeness,
  Spec §FR-024]
- [ ] CHK043 Is the current account-scoped GitHub connector discovered dynamically and JIT
  authorized, with no GitHub token or stale connector id? [Security, Spec §FR-025]
- [ ] CHK044 Is one injectable random wait policy of 1.5–4.0 seconds applied to every transport
  boundary, with fixed two-second loops forbidden? [Operability, Spec §FR-026]
- [ ] CHK045 Does homologation retain the exact prompt, all package files and upload status in
  the evidence directory even when external review is blocked? [Traceability, Spec §FR-027]
- [ ] CHK046 Does an incomplete GitHub response abort the attempt as
  `PENDING_EXTERNAL_REVIEW` without repair, second prompt, findings or task closure? [Failure
  handling, Spec §FR-028]
- [ ] CHK047 Are successful terminal JSON shape validation and external blocker serialization
  distinct, so an incomplete artifact is blocked rather than conversationally repaired?
  [Clarity, Spec §FR-029]
