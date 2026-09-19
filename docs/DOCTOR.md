# PowerPack doctor

`speckit.powerpack.doctor` is the read-only diagnostic surface for an installed PowerPack project. It is intentionally independent of `powerpack-delivery`: a broken workflow or custom step must still be diagnosable.

## Checks

The doctor validates:

- Specify CLI presence and minimum compatible Spec Kit version;
- initialized Spec Kit project;
- selected `sh`/`ps`/`py` runtime and parity with the materialized PowerPack command;
- active Spec Kit integration;
- PowerPack extension registration, enabled state, version and public commands;
- `powerpack-delivery` workflow registration and its checklist/task-plan/review convergence contract markers;
- `powerpack-control` custom-step registry and package completeness;
- Git executable, GitHub `origin` and working-tree state;
- Codex CLI and authentication required by the independent reviewer;
- exactly one enabled and available GitHub App/connector unless `--offline` is explicitly requested;
- active feature pointer/target when one exists;
- presence of `spec.md`, `plan.md`, `tasks.md`, reviewer checklist state and current PowerPack review state;
- when `tasks.md` exists, phase numbering/order, duplicate IDs, tasks outside phases, current pending phase and count of pending `[P]` opportunities.

The doctor reports `[P]` based only on explicit task markers. It does not invent parallelism or attempt to prove that two arbitrary tasks are safe to parallelize.

A dirty working tree is a warning, not a doctor failure, because mid-flight development is valid. A partially constructed feature without tasks is also valid. But `tasks.md` without `plan.md`, malformed phase structure, out-of-order phase execution, missing review prerequisites, stale PowerPack components, invalid feature pointers and runtime mismatches are failures.

## Output and exit code

Human-readable output is the default. `--json` emits `powerpack-doctor/v1` JSON with one result per check.

- exit `0`: no `FAIL` checks;
- exit `1`: at least one required check failed.

`WARN` means the installation is operable but the reported condition deserves attention. `SKIP` means the check is not applicable or was explicitly disabled.

The doctor never installs, repairs, edits artifacts, changes checklist markers, commits, pushes or mutates GitHub state.
