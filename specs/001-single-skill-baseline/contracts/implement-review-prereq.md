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
| `tasks.md` | `FEATURE_DIR/tasks.md` |
| SPEC base commit | `feature_base_commit(root, feature)` — the parent of the first commit that added `FEATURE_DIR/plan.md` (fallback `tasks.md`, then `FEATURE_DIR/`); the anchor commit itself when it is the repo root |
| SPEC delta | `git diff --name-only <SPEC base>..HEAD`, minus `.specify/powerpack/` |
| doc classification | existing `is_documentation_only()` |

## Evaluation

1. If `tasks.md` missing → `{"ok": false, "reason": "MISSING_TASKS"}`.
2. Parse task checkboxes (`- \[( |x|X)\] ` outside code fences). If any unchecked →
   `{"ok": false, "reason": "TASKS_INCOMPLETE", "unchecked": <n>, "total": <n>}`.
3. `git rev-parse --git-dir` fails → `{"ok": true, "reason": "OK", "git_unavailable": true}`
   (degraded: tasks-only).
4. `feature_base_commit` is `None` (the SPEC's own `plan.md`/`tasks.md` are not committed
   yet) → `{"ok": false, "reason": "NO_SPEC_BASELINE"}`.
5. Compute the **SPEC delta** — `git diff <SPEC base>..HEAD`, non-`.specify/powerpack/`.
   The working tree is **not** consulted: `implement-review` reviews a committed snapshot
   (its browserless gate requires `HEAD == PR head SHA`). If every path in the SPEC delta
   satisfies `is_documentation_only()` (or the delta is empty) →
   `{"ok": false, "reason": "NO_IMPLEMENTATION_DELTA"}`.
6. Otherwise → `{"ok": true, "reason": "OK"}`.

**Why SPEC-scoped.** Anchoring on the SPEC's own base commit means a *different* SPEC's
earlier code change on the same branch (or a re-used branch that already carries code)
does not count as this SPEC's implementation evidence — the property
`speckit.implement-review.md` states ("Evidence from another SPEC's directory never
satisfies this prerequisite") holds at runtime.

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
  **committed for this SPEC's era** and its tasks are complete.
- Consulting the working tree. Uncommitted work is invisible to this gate by design.
