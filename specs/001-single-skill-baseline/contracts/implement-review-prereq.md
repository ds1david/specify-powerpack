# Contract: Re-based `implement-review` Prerequisite Gate

**Purpose.** Replace the PowerPack `implement` state-receipt prerequisite with a
repository-evidence check, so `speckit.implement` can be removed without weakening the
"an explicit prior implementation must exist" guarantee (FR-018).

## Invocation (unchanged surface)

```
python .specify/powerpack/bin/powerpack.py prereq check --step implement-review [--feature-dir <dir>]
```

`speckit.implement-review.md` keeps calling exactly this. Exit `0` ⇒ proceed; non-zero ⇒
STOP and run upstream `speckit-implement` (hyphen — the upstream skill), not the removed
`speckit.implement` wrap.

## Inputs

| Input | How obtained |
|---|---|
| `FEATURE_DIR` | `--feature-dir` or `resolve_feature_dir()` (unchanged) |
| `tasks.md` existence | `FEATURE_DIR/tasks.md` (working tree) |
| `tasks.md` checkbox state | `git show HEAD:<FEATURE_DIR>/tasks.md` — the committed blob, never the working tree (working tree used only when git is unavailable). Only **implementation** checkboxes count: `count_implementation_checkboxes()` skips any checkbox line tagged `[ACCEPTANCE]` (case-insensitive) — post-review homologation that cannot precede `implement-review`. |
| SPEC base commit | `feature_base_commit(root, feature)` — the first commit that added `FEATURE_DIR/plan.md` (fallback `tasks.md`, then `FEATURE_DIR/`). The delta is computed **strictly after** this commit, so its own tree is the planning baseline. |
| SPEC delta | `git diff --name-only <SPEC base>..HEAD`, minus `.specify/powerpack/` |
| doc classification | existing `is_documentation_only()` |

## Evaluation

Every check reads the committed snapshot at `HEAD`; the working tree is consulted only
for `tasks.md` *existence* (step 1) and, when git is unavailable, for checkbox state
(step 3). `implement-review` reviews a committed snapshot — its browserless gate requires
`HEAD == PR head SHA`.

1. If `FEATURE_DIR/tasks.md` is missing from the working tree →
   `{"ok": false, "reason": "MISSING_TASKS"}`.
2. `git rev-parse --git-dir` fails → skip to the degraded path: parse *implementation*
   checkboxes from the working-tree `tasks.md` (`[ACCEPTANCE]` lines skipped); any unchecked
   (or none present) →
   `{"ok": false, "reason": "TASKS_INCOMPLETE", "unchecked": <n>, "total": <n>}`, otherwise
   `{"ok": true, "reason": "OK", "git_unavailable": true}`. Steps 3–6 are git-only.
3. `git show HEAD:<FEATURE_DIR>/tasks.md` does not resolve (the SPEC's own `tasks.md` is not
   committed yet) → `{"ok": false, "reason": "NO_SPEC_BASELINE"}`.
4. Parse *implementation* checkboxes from that committed blob (`- \[( |x|X)\] ` outside code
   fences, skipping any line containing `[ACCEPTANCE]`). If any unchecked (or none present) →
   `{"ok": false, "reason": "TASKS_INCOMPLETE", "unchecked": <n>, "total": <n>}` — counts
   are over the implementation set only.
5. `feature_base_commit` is `None` (no commit introduced the SPEC's `plan.md`/`tasks.md`/
   directory) → `{"ok": false, "reason": "NO_SPEC_BASELINE"}`.
6. Compute the **SPEC delta** — `git diff <SPEC base>..HEAD`, non-`.specify/powerpack/`,
   i.e. everything committed **strictly after** the SPEC's introduction commit. If every
   path satisfies `is_documentation_only()` (or the delta is empty) →
   `{"ok": false, "reason": "NO_IMPLEMENTATION_DELTA"}`. Otherwise →
   `{"ok": true, "reason": "OK"}`.

**Why SPEC-scoped.** Anchoring on the SPEC's introduction commit — and taking the delta
*strictly after* it — means neither a *different* SPEC's earlier code change on the same
branch (or a re-used branch that already carries code) nor an unrelated non-doc change
bundled into this SPEC's own introduction commit counts as this SPEC's implementation
evidence. The property `speckit.implement-review.md` states ("Evidence from another SPEC's
directory never satisfies this prerequisite") holds at runtime, and a real implementation
commit must land *after* `/speckit-plan` + `/speckit-tasks`.

## Output (stdout JSON)

```json
{ "ok": true, "step": "implement-review", "feature": "<feature-id>", "reason": "OK" }
```

Failure adds `reason` from the enum (`MISSING_TASKS` / `TASKS_INCOMPLETE` /
`NO_SPEC_BASELINE` / `NO_IMPLEMENTATION_DELTA`), an optional `detail` string, and where
relevant `unchecked` / `total` / `git_unavailable`. Exit `0` when `ok`, else `9` with
`next_action: "speckit-implement"`.

## Config

`.specify/powerpack/prerequisites.json` (written by `cli.py install_support`):

```json
{
  "schema_version": 2,
  "mode": "strict",
  "steps": {
    "implement-review": [{ "check": "implementation-evidence" }]
  }
}
```

- `checklist-converge` entry removed (command removed).
- `mode: "off" | "disabled"` still short-circuits to `ok: true` (unchanged).
- Unknown/legacy `[{ "step": "implement", "statuses": ["COMPLETED"] }]` shape, if found in a
  pre-existing project file, is treated as "use the built-in `implementation-evidence`
  check" (forward-compat; no crash).

## Non-goals

- Perfect file↔SPEC attribution. Timeline scoping catches the common case (another SPEC's
  code committed *before* this SPEC's baseline). Two SPECs whose implementation commits
  interleave on one branch can still cross-satisfy — that is an unusual workflow and is left
  to the reviewer / the browserless PR gate, which pins an exact PR + changed-file set.
- Detecting *who* implemented (agent vs human) — only that a real non-doc change was
  **committed strictly after this SPEC's plan/tasks** and its committed *implementation*
  tasks are complete.
- Gating on homologation. A `[ACCEPTANCE]`-tagged task (e.g. the T025 live browserless
  round-trip) is validated *after* `implement-review` and is not counted here; its evidence
  is a PR-review artefact (`T025-evidence/`), not a runtime signal. Abusing the tag to skip
  real implementation work is a review concern, like any dishonest checkbox.
- Consulting the working tree, beyond checking that `tasks.md` exists. Checkbox state and
  the implementation delta both come from `HEAD`; uncommitted work — including locally
  ticked checkboxes — is invisible to this gate by design. (Exception: when git is
  unavailable the gate degrades to a working-tree checkbox scan, flagged `git_unavailable`.)
