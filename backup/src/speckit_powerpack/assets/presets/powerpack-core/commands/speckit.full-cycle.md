---
description: "Orchestrate one same-SPEC cycle through clarification, planning, explicit implementation and integrated convergence/review."
---

# SpecKit Full Cycle

This command orchestrates existing Spec Kit and PowerPack primitives. It does not duplicate their internal logic and does not replace official Spec Kit stages.

Canonical top-level flow:

```text
speckit-clarify
  -> speckit-plan
  -> speckit-checklist
  -> speckit-checklist-converge
  -> speckit-tasks
  -> speckit-analyze
  -> speckit-implement
  -> speckit-implement-review
  -> DONE
```

`specify` normally creates/selects the SPEC before the cycle starts. The initial `speckit-implement` is mandatory and explicit; `speckit-implement-review` cannot manufacture that predecessor.

## Core invariants

- Resolve exactly one SPEC and never switch SPEC implicitly.
- Preserve `DISCOVER CAPABILITY -> SELECT STRATEGY -> EXECUTE CONTRACT`.
- Never bypass a blocked prerequisite, constitution conflict, failed gate or unresolved finding.
- Never convert convergence/review obligations to technical debt merely to finish the cycle.
- `implement_review` requires the same-SPEC completed `implement` receipt.
- Findings and convergence gaps discovered after implementation stay inside the active `implement-review` loop.
- `implement_review` must pass `speckit-powerpack doctor . --strict-review` before material review work.
- No PowerPack full-cycle step authorizes merge, GitHub approval, ready-for-review, force-push or destructive reset.
- `DONE` requires the independent Sol/xhigh gate and the browserless ChatGPT Project + GitHub gate to approve the same final immutable snapshot.

## Terminal UX and routing

Before the first material phase, read `.specify/powerpack/model-routing.json` and show the planned routing rows for phases that will actually run. On Codex, the packaged defaults use Terra/high for orchestration/implementation, Luna for bounded economical work, Sol for semantic gates/review, and the separate browserless Project+GitHub review provider after Sol is clean.

Never fabricate timing, tool counts, diffs or review evidence.

## Configuration

Read `.specify/powerpack/full-cycle.json`. Projects may change enabled optional pre-implementation phases, mode and round limits, but must not weaken:

- `same_spec_only=true`;
- `stop_on_blocked=true`;
- `allow_debt_escape_hatch=false`;
- `explicit_initial_implement_required=true`;
- `implement_review_owns_convergence=true`.

## Start / resume state

After resolving the target SPEC:

```bash
python .specify/powerpack/bin/full_cycle.py start \
  --feature-dir <SPEC_DIR> \
  --mode <interactive|auto>
```

If a run exists:

```bash
python .specify/powerpack/bin/full_cycle.py status --feature-dir <SPEC_DIR>
```

The returned `current_phase` is authoritative.

## Phase execution

| Runtime phase | Command |
|---|---|
| `clarify` | `speckit-clarify` |
| `plan` | `speckit-plan` |
| `checklist` | `speckit-checklist` when applicable |
| `checklist_converge` | `speckit-checklist-converge` |
| `tasks` | `speckit-tasks` |
| `analyze` | `speckit-analyze` |
| `implement` | `speckit-implement` |
| `implement_review` | `speckit-implement-review` |

After a normal deterministic phase succeeds:

```bash
python .specify/powerpack/bin/full_cycle.py advance \
  --feature-dir <SPEC_DIR> \
  --phase <phase> \
  --outcome completed \
  --evidence "concise verifiable result"
```

If checklist is not applicable, record `--outcome skipped`; do not fake an execution receipt.

## Explicit initial implementation

After `analyze` is clean, enter `implement`, run `speckit-implement` completely and record its same-SPEC implementation receipt. The next top-level phase is `implement_review`, not a standalone `converge` phase.

## Integrated implementation-review

Before review work:

```bash
speckit-powerpack doctor . --strict-review
speckit-powerpack review status --path . --live
```

Readiness requires the installed PowerPack runtime, Codex CLI/authentication, an explicit ChatGPT Project binding and a live GitHub App/connector. Missing readiness is `BLOCKED_CONFIGURATION`; there is no browser/Web2API fallback.

The active `implement_review` phase owns:

```text
converge
  -> tasks appended? implement -> converge ...
  -> capability-selected quality gate
  -> independent Sol/xhigh review
       -> findings? implement fixes -> converge -> quality gate -> Sol review ...
  -> browserless ChatGPT Project + GitHub review
       -> immutable GitHub PR manifest
       -> Deep Review Protocol 2.0
       -> findings? implement fixes -> converge -> quality gate -> fresh Sol -> fresh Project+GitHub review
  -> both gates approve same final snapshot
```

The GitHub review requires an explicit PR and local `HEAD == PR head SHA`. GitHub evidence must come through the selected `codex_apps` MCP connector; shell/web-search fallback cannot satisfy the gate.

Do not advance full-cycle state on intermediate findings or convergence gaps.

Only after both review gates approve the same final snapshot:

```bash
python .specify/powerpack/bin/full_cycle.py advance \
  --feature-dir <SPEC_DIR> \
  --phase implement_review \
  --outcome approved \
  --evidence "convergence clean; quality gate green/N-A; Sol and browserless Project+GitHub review approved same snapshot"
```

## Review budget

If configured budget is exhausted before approval, return `BLOCKED_BUDGET`. Never extend a review or convergence budget silently.

## Blocking and resume

If a phase is materially blocked:

```bash
python .specify/powerpack/bin/full_cycle.py advance \
  --feature-dir <SPEC_DIR> \
  --phase <phase> \
  --outcome blocked \
  --evidence "blocker / owner-stage handoff"
```

Use the natural owner-stage repair path: requirements/scope -> specify/clarify, design -> plan, decomposition -> tasks, implementation -> implement. Re-run derived gates after repair.

After a legitimate blocker is resolved:

```bash
python .specify/powerpack/bin/full_cycle.py resume --feature-dir <SPEC_DIR> --unblock
```

Abort removes only ephemeral cycle state; SPEC artifacts, implementation changes, receipts and review findings remain.

## Completion

`DONE` means the same SPEC passed its explicit implementation predecessor, integrated convergence, capability-selected quality gate, independent Sol/xhigh review and browserless ChatGPT Project + GitHub review on one final immutable snapshot. It does not mean a PR was approved or authorized to merge.
