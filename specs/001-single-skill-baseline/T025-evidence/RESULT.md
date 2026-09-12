# T025 / T051 / T057 — Validation Runbook Result

**Run date:** 2026-09-10
**Branch / commit under test:** `feat/spec-001-single-skill-baseline` @ `349a6f687e7e16711b7cf9037e88ba0627b20070` (= PR #15 head)
**Target repository:** `ds1david/specify-powerpack` (renamed from `speckit-powerpack`)
**Executed by:** live round-trip from a disposable git worktree at HEAD, PowerPack self-installed.

## Verdict

| Dimension | Result |
|---|---|
| Runbook mechanism (S1–S7 reachable, browserless, real services) | **PASS** |
| SC-003 *process* property (no step fails due to a removed command / helper / config) | **PASS** |
| Deep-review *content* verdict | **`CHANGES_REQUIRED`** (4 findings) |
| T025 / T051 / T057 checkbox state | **stays `[ ]`** — the gate we ran returned `CHANGES_REQUIRED` |

The live Codex → ChatGPT Project → GitHub round-trip **works end to end**. It is no longer
"unverified". But the deep review it produced is not `APPROVED`, so the acceptance tasks
are not complete.

## Stage results

| Stage | Command / check | Result | Evidence |
|---|---|---|---|
| P1 | PowerPack installed from branch → `bin/` | `capabilities.py`, `powerpack.py`, `review_protocol.py` only | `P1-bin.txt` |
| P2 | `powerpack-core` preset command set | `== {speckit.implement-review}` | `P2-commands.txt` |
| P3 | upstream `speckit-implement` + `speckit-converge` present | yes (`.claude/skills/`) | `P3-upstream.txt` |
| P4 | Codex CLI + `codex login` | `codex` 0.153.4, `~/.codex/auth.json` present | `S1-doctor.txt` |
| P5 | repo ↔ ChatGPT Project + GitHub App | bound to `speckit-powerpack` (`g-p-6a9ba1a0…`); GitHub App `READY`, OAuth `ACTIVE` | `S1-review-status.txt` |
| P7 | PR head == local HEAD | `349a6f6…` == `349a6f6…` | `S6-review-run.txt` snapshot |
| S1 | `doctor . --strict-review` | `specify` / `spec-kit-project` / `powerpack-runtime` / `selected-executor` **OK**; no missing-PowerPack-file FAIL | `S1-doctor.txt` |
| S2 | `prereq check --step implement-review` (FR-018a) | `TASKS_INCOMPLETE` (`unchecked: 3` = T025/T051/T057) — deterministic; gate reads committed `HEAD` | `S2-prereq.json` |
| S2- | four failure reasons reproduced | `MISSING_TASKS`, `TASKS_INCOMPLETE`, `NO_IMPLEMENTATION_DELTA`, `NO_SPEC_BASELINE` | `S2-negatives.txt` |
| S4 | `gate detect` / `gate run` | `REQUIRED / python / pytest` — real delta, not a false `NOT_APPLICABLE`; `capabilities.py` free of `implement_runs` / `latest_implement_files` | `S4-*.txt` |
| S5 | `review route` + `model-routing` stages | `READY / codex / gpt-5.6-sol / xhigh / read-only`; `stages == {implement-review}` | `S5-*.json` |
| S6 | `review run --path . --pr 15` | **`CHANGES_REQUIRED`**, `BROWSERLESS_CODE_REVIEW_COMPLETED`; `browser_used=false`, `cdp_used=false`, `playwright_used=false`, `web2api_used=false`; real `github.*` App tool calls; first run hit the 600 s default timeout → re-run with `--timeout 3300` | `S6-review-run.txt`, `review.json` |
| S7 | `review_protocol.py validate --input review.json` | `valid: true`, `schema_version: "2.0"`, `errors: []` | `S7-protocol-validate.txt` |
| S3 | upstream `/speckit-converge` (live agent) | **not run** — would mutate SPEC-001 `tasks.md`; upstream command presence proven statically (P3) and `speckit.implement-review.md` Phase 1 references the upstream hyphen form | — |
| §3 offline collector | `collect-t025-offline-evidence.sh` | **PASS** (11/11 checks) | `_collector-run.txt` |

## Deep-review findings (`review.json`, round 1, reviewer `codex`)

Ran on SPEC + GitHub PR evidence only — **`project_context_evidence.literal_evidence` =
"conversation could not be loaded"**, so the ChatGPT Project serialized context (and the
round-1 / round-2 review history it holds) was **not** consumed. GitHub side fully worked
(all 57 patches, 89 files inspected).

| ID | Sev | Title | Assessment |
|---|---|---|---|
| R001-002 | HIGH | The immutable head cannot pass its own prerequisite or SC-003 gate | The T025/T051/T057 circular-checkbox gate. Self-resolves when the flow is executed *and* honestly recorded — or the review's alternative: revise the durable lifecycle contract so acceptance/homologation tasks are not gated by `implement_evidence`. **This run is that execution; the verdict is not yet APPROVED.** |
| R001-001 | HIGH | Normal updates retain removed command runtimes and configuration | Real behaviour: `install_support` stopped *copying* `powerpack_debt.py` / `powerpack_full_cycle.py` / their configs, but a normal `update` never *unlinks* them from an existing install, and `write_json` keeps old routing/prereq entries unless `--reset-config`. Touches FR-003 / FR-012. **Scope-debatable** — spec.md line 398 states "no migration shim is provided", and FR-006 / FR-010 target *fresh* install state. Needs an explicit scope decision. |
| R001-003 | MED | The installed exact-set contract is not tested | `test_baseline_contract.py::test_installed_support_has_no_removed_command_assets` calls `install_support` only and checks `bin/*.py` + a file blocklist; it never installs the preset boundary and asserts `installed_powerpack_commands == {speckit.implement-review}` (FR-011). Source side is covered; installed side is not. Fair. |
| R001-004 | MED | The behavioral removal check never invokes the real dispatcher | `test_removed_command_names_are_unknown_to_the_runtime_parser` inspects argparse choices + `hasattr` only; removed *preset* commands (`full-cycle`, `debt-*`) were never `powerpack.py` verbs. FR-014 asks for invocation "at the command registration/dispatch layer" against a clean install. The current test is weaker than FR-014 requires. Fair. |

Requirement statuses the review assigned: FR-003 / FR-010 / FR-011 / FR-012 / FR-014 / SC-003 → **FAIL**; FR-001 / FR-004 / FR-006 / FR-015 / FR-019 / SC-001 / SC-004 / SC-005 / SC-006 → PARTIAL; rest PASS. Several of the FAIL/PARTIAL calls (FR-006, FR-012) warrant independent verification — the reviewer lacked the Project history.

## What this establishes

1. The single preserved capability's browserless review path **runs to a valid terminal
   state through real Codex + GitHub services** — SC-003's "no step fails due to a removed
   command/helper" property holds at runtime, not just in mocked tests.
2. The FR-018a prerequisite gate behaves exactly as specified against a committed `HEAD`
   (`TASKS_INCOMPLETE` for the 3 open acceptance boxes).
3. The deep review is **not `APPROVED`**. T025 / T051 / T057 remain `[ ]`. The 4 findings
   need triage → an implementation round (or, for R001-001, a scope decision) → a re-run
   that reaches `APPROVED` (or a documented, contract-level resolution of the circular gate
   in R001-002).

## Round 3 remediation (2026-09-10, commits `ee3da40`…`a6035d9`)

The 4 findings above were addressed:

| Finding | Fix | Status |
|---|---|---|
| R001-002 | `[ACCEPTANCE]` tag — `count_implementation_checkboxes()` excludes post-review homologation tasks from the FR-018a gate. Verified: `prereq check` on the new HEAD returns `{"ok": true, "reason": "OK"}`. | done (T058) |
| R001-001 | `cli._prune_removed_command_state()` — a normal `update` now unlinks retired removed-command runtimes/configs and strips removed-command routing/prereq keys. | done (T059) |
| R001-003 | `test_installed_powerpack_command_namespace_is_exactly_implement_review` — real `specify preset add` composition, equality assertion; new `installed-contract` CI job. | done (T060) |
| R001-004 | `test_removed_command_names_are_undispatchable_after_a_real_install` — real resolver, no materialised command file for any removed name. | done (T061) |
| infra | `.devcontainer/` + `homologate.sh` reproduce this homologation. | done (T063) |

CI matrix + `installed-contract` job green on `a6035d9`. Full suite: 106 passed.

**Re-homologation (T062) is pending** — to be run by the maintainer:
`bash .devcontainer/homologate.sh 15 --project <g-p-id-or-url>` (the ChatGPT Project is
named `specify-powerpack`, id `g-p-6a9ba1a060208191a5b6e03a3950b183`; pass the id or its
URL, not the bare name). This section and the `[ACCEPTANCE]` task checkboxes close when that
run returns `APPROVED` + a valid `S7`.

## Environmental notes

- `origin` in the main checkout still points at the pre-rename URL
  (`github.com/ds1david/speckit-powerpack`); the GitHub connector rejects the old name, so
  the worktree's `origin` was repointed to `…/specify-powerpack`. Worth fixing in the main
  checkout.
- `review run` default `--timeout` (600 s) is too short for an xhigh deep review of a
  57-file delta; needed `--timeout 3300`.
- The ChatGPT Project serialized context failed to load for this review
  ("conversation could not be loaded").
