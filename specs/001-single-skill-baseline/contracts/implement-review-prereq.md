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
| repo file set | `git ls-files -co --exclude-standard` (existing `git_candidate_files`) |
| doc classification | existing `is_documentation_only()` |

## Evaluation

1. If `tasks.md` missing → `{"ok": false, "reason": "MISSING_TASKS"}`.
2. Parse task checkboxes (`^\s*- \[( |x|X)\]` outside code fences). If any unchecked →
   `{"ok": false, "reason": "TASKS_INCOMPLETE", "unchecked": <n>}`.
3. Determine `git_available` (`git rev-parse --git-dir`). If unavailable →
   skip step 4, set `git_unavailable: true`.
4. Compute the changed non-`.specify/powerpack/` file set (tracked-modified + untracked).
   If every changed path satisfies `is_documentation_only()` (or the set is empty) →
   `{"ok": false, "reason": "NO_IMPLEMENTATION_DELTA"}`.
5. Otherwise → `{"ok": true, "reason": "OK"}`.

## Output (stdout JSON)

```json
{ "ok": true, "step": "implement-review", "feature": "<feature-id>", "reason": "OK" }
```

Failure adds `reason` from the enum above and, where relevant, `unchecked` (int) or
`git_unavailable` (bool). Exit code: `0` when `ok`, else the existing failure code path of
`cmd_prereq_check` (non-zero; keep `9`-style semantics with `next_action:
"speckit-implement"`).

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

- Cross-SPEC protection beyond what `resolve_feature_dir()` already gives.
- Detecting *who* implemented (agent vs human) — only that a real non-doc delta exists and
  tasks are complete.
