# Implementation execution contract

PowerPack does not implement its own task scheduler. The execution authority is the combination of the active feature's `plan.md`, `tasks.md`, and the upstream `speckit.implement` command.

## Phase order

`tasks.md` is generated as ordered implementation phases. PowerPack validates that executable tasks live under `## Phase N: ...` headings and that phase numbers are unique and ordered.

Implementation must complete the current pending phase before moving to a later phase. If an adopted feature already contains completed tasks in a later phase while an earlier phase is still pending, PowerPack treats the task state as inconsistent instead of silently normalizing it.

The implementation strategy and architecture in `plan.md` remain authoritative for where work belongs and how the phases compose.

## Parallel tasks

The Spec Kit `[P]` marker is the only authorization for task-level parallel execution.

A task may be marked `[P]` only when:

- it touches different files from work that would conflict;
- it has no dependency on incomplete tasks;
- it can be completed independently inside the current phase.

Tasks without `[P]` are sequential. Tasks that share files or dependency edges are sequential even if running them concurrently would appear faster.

PowerPack does not infer new parallelism and does not create workflow branches for individual tasks. `speckit.implement` owns the actual scheduling because it already defines phase-by-phase execution, dependency enforcement, same-file coordination, TDD ordering and validation checkpoints.

## Execution path

Before every implementation entry point PowerPack validates the task plan with the `powerpack-control/task-plan` action. It reports:

- number of phases;
- total/completed/pending tasks;
- current pending phase;
- pending `[P]` opportunities;
- structural inconsistencies such as duplicate task IDs, out-of-order phases or tasks outside a phase.

Then PowerPack calls `speckit.implement`.

After the command returns, PowerPack validates the task plan again. A successful implementation step is not accepted if pending tasks remain.

## Convergence

When `speckit.converge` changes or appends work in `tasks.md`, PowerPack re-parses the task plan. Newly created work is not executed directly by a remediation prompt. It is passed to `speckit.implement`, so convergence tasks follow the same phase and `[P]` semantics.

## Review remediation

Independent-review findings are first translated into explicit remediation tasks.

The planning step must:

1. keep every finding mandatory;
2. update active SPEC traceability where required;
3. create implementation/test/project-documentation tasks;
4. place those tasks in the dependency-correct phase;
5. add `[P]` only when the standard Spec Kit parallelization rules are satisfied;
6. avoid modifying implementation code directly.

Only after the remediation task plan is valid does PowerPack invoke `speckit.implement`.

This preserves one implementation executor for initial implementation, mid-flight continuation, convergence work and review remediation.
