# PowerPack architecture

PowerPack composes Spec Kit rather than replacing its SDD semantics.

## Public surface

- `speckit.powerpack.deliver`: resumable feature delivery.
- `speckit.powerpack.doctor`: read-only installation/runtime/task-plan/review diagnostics.

## Runtime components

```text
PowerPack extension
├── deliver command (sh / ps / py launcher)
└── doctor command  (sh / ps / py launcher)

powerpack-delivery workflow
└── powerpack-control custom step
    ├── adoption/state inspection
    ├── checklist inspection
    ├── plan/tasks execution validation
    ├── tasks fingerprinting
    └── independent review
```

Workflow orchestration remains in `workflow.yml`; the custom step provides deterministic machine-readable facts. The doctor lives in the extension so it remains usable even when the workflow/step installation is damaged.

## Implementation authority

`plan.md`, `tasks.md` and upstream `speckit.implement` are the implementation execution authority.

PowerPack validates phase structure and pending work but deliberately does not implement another scheduler. `speckit.implement` owns phase-by-phase execution, task dependency ordering, TDD ordering, explicit `[P]` opportunities, same-file serialization, validation checkpoints and `[X]` progress markers.

Initial implementation, mid-flight continuation, convergence work and review remediation all use this same executor.

## Distribution

Normal consumers use immutable versioned release assets: an extension ZIP with `extension.yml` at archive root, a workflow ZIP with `workflow.yml` at archive root, and a versioned PowerPack-owned step catalog pinned to the same Git tag. Local `--dev` installation is reserved for PowerPack development.

## Archive boundary

The complete pre-rewrite repository is preserved under `backup/`. Active extension, workflow and step code never imports, loads, executes or resolves templates/state from that archive.
