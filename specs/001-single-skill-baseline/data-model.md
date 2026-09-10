# Phase 1 Data Model: Single Skill Baseline

This feature has no runtime domain data. The "entities" are the artifacts the cleanup
produces and the state the re-based gate reads.

## Command Inventory Record

Produced before any deletion (FR-002). One row per `powerpack-core` command present at the
baseline SHA.

| Field | Type | Notes |
|---|---|---|
| `name` | string | `provides.templates[].name` from `preset.yml`, e.g. `speckit.implement-review` |
| `command_file` | path | `commands/<name>.md` |
| `runtime_modules` | path[] | stdlib modules under `assets/runtime/` used only by this command |
| `config_keys` | string[] | keys/files under `assets/config/` and `.specify/powerpack/` used only by this command |
| `installer_refs` | location[] | lines in `cli.py` / `install.*` that copy or wire this command |
| `doc_refs` | path[] | docs whose subject is this command |
| `tests` | path[] | test modules / cases dedicated to this command |
| `shared_deps` | path[] | helpers also used by `implement-review` or core (must NOT be deleted) |
| `decision` | enum | `PRESERVE` \| `REMOVE` — only `speckit.implement-review` may be `PRESERVE` |

**Validation.** Exactly one row has `decision = PRESERVE`. The union of `REMOVE` rows'
`shared_deps` is disjoint from the set of files actually deleted.

## Exact-Set Baseline Contract

The invariant encoded by the regression guard (FR-011, FR-017).

| Field | Type | Value |
|---|---|---|
| `namespace` | string | `powerpack-core` preset (`provides.templates`) |
| `expected` | set<string> | `{"speckit.implement-review"}` |
| `registration_actual` | set<string> | parsed from `preset.yml` in the asset tree |
| `install_actual` | set<string> | enumerated from a clean install into a temp project |

**Validation.** `registration_actual == expected` **and** `install_actual == expected`
(equality, not membership). Out of scope for this set: `powerpack-tools` extension commands,
upstream `speckit-*` skills.

## Reference Classification

Produced after deletion (FR-016). One row per repository occurrence of a removed command
name (`speckit.implement`, `speckit.converge`, `speckit.checklist-converge`,
`speckit.full-cycle`, `speckit.debt-*`, and the `full_cycle` / `debt` / `technical-debt`
tokens).

| Field | Type | Notes |
|---|---|---|
| `path` | path | file + line |
| `token` | string | the matched removed name/token |
| `class` | enum | `ACTIVE_REFERENCE` \| `HISTORICAL_REFERENCE` \| `FALSE_POSITIVE` |
| `justification` | string | required for `HISTORICAL_REFERENCE` / `FALSE_POSITIVE` |

**Validation.** `count(class == ACTIVE_REFERENCE) == 0` for every removed token.
`HISTORICAL_REFERENCE` allowed only in changelog / completed-spec / ADR / merged-PR context
and must not imply current support.

## Re-based Prerequisite Evidence

The state the re-based `implement-review` gate reads (D1). No new persisted file — it is
derived live.

| Signal | Source | Pass condition |
|---|---|---|
| `tasks_present` | `FEATURE_DIR/tasks.md` exists | true |
| `tasks_complete` | all `- [ ]`/`- [x]` lines in `tasks.md` | zero unchecked |
| `spec_base` | `feature_base_commit(root, feature)` — parent of the commit that added the SPEC's `plan.md`/`tasks.md`/dir | resolvable (SPEC artifacts are committed) |
| `spec_implementation_delta` | `git diff <spec_base>..HEAD`, minus `.specify/powerpack/`, vs `is_documentation_only()` | ≥1 non-doc file **committed for this SPEC's era**; working tree not consulted |
| `git_available` | `git rev-parse --git-dir` succeeds | if false → evaluate `tasks_*` only, annotate `git_unavailable: true` |

**Output (JSON, stdout):** `{"ok": bool, "step": "implement-review", "feature": "<id>",
"reason": "<OK|MISSING_TASKS|TASKS_INCOMPLETE|NO_SPEC_BASELINE|NO_IMPLEMENTATION_DELTA>",
"unchecked": <int?>, "total": <int?>, "detail": <str?>, "git_unavailable": <bool?>}`. Exit
`0` when `ok`, else `9` with `next_action: "speckit-implement"`.

**Cross-SPEC rejection (FR-018a).** Because the delta is `<spec_base>..HEAD`, a SPEC whose
`plan.md` was committed *after* another SPEC's code change does not see that change in its
delta. Encoded by `test_implement_evidence_rejects_other_specs_code_delta`.

## State transitions

None. The feature is a one-way scope reduction. The only lifecycle note: a future
`powerpack-core` command may be re-added **only** by an explicit new spec that changes the
Exact-Set Baseline Contract (FR-017).
