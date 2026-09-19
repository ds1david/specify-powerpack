# Specify PowerPack

Specify PowerPack adds two public capabilities to GitHub Spec Kit:

- `speckit.powerpack.deliver`
- `speckit.powerpack.doctor`

`deliver` can start a new feature or adopt an existing SPEC mid-flight and automate only the remaining lifecycle. `doctor` is a read-only diagnostic that validates the installed PowerPack stack, Spec Kit runtime selection, review prerequisites and active feature state.

## Delivery flow

```text
inspect/adopt
-> missing SDD phases only
-> checklist-converge
-> analyze (advisory freshness report)
-> implement
-> implement <-> converge until tasks.md is stable
-> prepare exact PR/HEAD
-> independent review
   -> findings -> mandatory remediation + project docs + SPEC docs
   -> converge -> republish -> review
   -> APPROVED only with zero findings
```

A manual sequence such as clarify -> plan -> checklist -> tasks -> analyze is adopted at the post-tasks checkpoint. Existing artifacts are preserved. PowerPack converges reviewer-owned checklists, re-runs analyze because it has no durable success artifact, then continues with implementation.

Every independent-review finding is mandatory current-delivery work, including suggestions, nits, warnings, hardening and documentation findings. Findings may not be deferred. Remediation must keep implementation/tests, project documentation and the active SPEC artifacts synchronized.

## Script-runtime parity

Both public commands ship Bash, PowerShell and Python launchers using the same scripts frontmatter mechanism as Spec Kit core commands. Spec Kit resolves `{SCRIPT}` according to the project's `.specify/init-options.json` selection: `sh`, `ps`, or `py`.

The custom `powerpack-control` workflow step is Python because workflow steps execute inside the Spec Kit Python engine; it is not a project shell helper.

## Start here

- Installation and usage: [docs/INSTALLATION_AND_USAGE.md](docs/INSTALLATION_AND_USAGE.md)
- Doctor: [docs/DOCTOR.md](docs/DOCTOR.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Mid-flight adoption: [docs/MIDFLIGHT_ADOPTION.md](docs/MIDFLIGHT_ADOPTION.md)
- Checklist convergence: [docs/CHECKLIST_CONVERGENCE.md](docs/CHECKLIST_CONVERGENCE.md)
- Delivery workflow: [docs/DELIVERY_WORKFLOW.md](docs/DELIVERY_WORKFLOW.md)
- Script runtime: [docs/SCRIPT_RUNTIME.md](docs/SCRIPT_RUNTIME.md)
- Independent review: [docs/REVIEW.md](docs/REVIEW.md)
- Migration: [docs/MIGRATION.md](docs/MIGRATION.md)
