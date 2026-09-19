# PowerPack architecture

PowerPack is composed from Spec Kit primitives and keeps the public surface intentionally small.

## Public commands

- `speckit.powerpack.deliver` launches the resumable delivery workflow.
- `speckit.powerpack.doctor` diagnoses installation/runtime/review readiness without entering the workflow.

Both commands use Spec Kit command frontmatter with `sh`, `ps` and `py` script variants. The selected runtime comes from the initialized Spec Kit project.

## Installed components

```text
powerpack extension
├── deliver command
├── doctor command
└── runtime launchers

powerpack-delivery workflow
└── powerpack-control custom step
    ├── adoption/state inspection
    ├── checklist status
    ├── tasks fingerprinting
    └── independent review
```

The custom workflow step is distributed through `catalogs/step-catalog.json` because current Spec Kit installs third-party workflow steps through step catalogs.

## Doctor isolation

Doctor is deliberately implemented inside the extension rather than the `powerpack-control` step. It must remain usable when the workflow or custom step is missing, stale, or corrupted. It is read-only and may inspect installation metadata, Git, Codex authentication, GitHub App availability and active feature artifacts.

## Delivery and review convergence

Delivery composes upstream Spec Kit phases rather than replacing them. Checklist convergence precedes implementation; implementation convergence uses `speckit.converge` and task fingerprints; independent review is bound to an exact pushed PR HEAD.

Every valid review finding is mandatory current-delivery work, including low-severity suggestions and documentation findings. Remediation keeps implementation/tests, project documentation and active SPEC artifacts synchronized before re-convergence and re-review.

## Archive boundary

The active runtime under `extensions/`, `workflows/` and `steps/` must not reference `backup/`. The archive exists only as historical source material.
