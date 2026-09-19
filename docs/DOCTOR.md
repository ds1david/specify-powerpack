# PowerPack doctor

`speckit.powerpack.doctor` is the read-only diagnostic surface for an installed PowerPack project. It is intentionally independent of `powerpack-delivery`: a broken workflow or custom step must still be diagnosable.

## Checks

The doctor validates:

- Specify CLI presence and minimum compatible Spec Kit version;
- initialized Spec Kit project;
- selected `sh`/`ps`/`py` runtime and parity with the materialized PowerPack command;
- active Spec Kit integration;
- PowerPack extension registration, enabled state, version and public commands;
- `powerpack-delivery` workflow registration and required convergence/remediation contract markers;
- `powerpack-control` custom-step registry and package completeness;
- Git executable, GitHub `origin` and working-tree state;
- Codex CLI and authentication required by the independent reviewer;
- exactly one enabled and available GitHub App/connector unless `--offline` is explicitly requested;
- active feature pointer/target when one exists;
- presence of `spec.md`, `plan.md`, `tasks.md`, reviewer checklist state and current PowerPack review state.

A dirty working tree is a warning, not a doctor failure, because mid-flight development is valid. Missing review prerequisites, stale/missing PowerPack components, invalid feature pointers and runtime mismatches are failures.

## Output and exit code

Human-readable output is the default. `--json` emits `powerpack-doctor/v1` JSON with one result per check.

- exit `0`: no `FAIL` checks;
- exit `1`: at least one required check failed.

`WARN` means the installation is operable but the reported condition deserves attention. `SKIP` means the check is not applicable or was explicitly disabled, such as the GitHub App connectivity probe under `--offline`.

## Examples

```text
speckit.powerpack.doctor
speckit.powerpack.doctor spec-soak-003
speckit.powerpack.doctor --json
speckit.powerpack.doctor --offline
```

The doctor never installs, repairs, edits artifacts, changes checklist markers, commits, pushes or mutates GitHub state. It reports remediation instructions and leaves changes to the operator or delivery workflow.
