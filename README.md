# Specify PowerPack

Specify PowerPack adds two public capabilities to GitHub Spec Kit:

- `speckit.powerpack.deliver`
- `speckit.powerpack.doctor`

`deliver` starts or adopts a SPEC and automates the remaining delivery lifecycle. `doctor` validates the installed PowerPack stack, runtime, implementation task-plan discipline, review prerequisites and active feature state.

## Standard install

Normal consumers should install immutable release assets, not clone the repository:

```bash
specify extension add powerpack --from \
  https://github.com/ds1david/specify-powerpack/releases/download/v0.4.0/specify-powerpack-extension-v0.4.0.zip
```

Then install the matching versioned control step and workflow as documented in [docs/INSTALLATION_AND_USAGE.md](docs/INSTALLATION_AND_USAGE.md).

`--dev` installation is reserved for PowerPack development.

## Delivery model

```text
adopt -> missing SDD phases -> checklist-converge -> analyze
      -> validate plan.md + tasks.md
      -> speckit.implement
           -> phases in order
           -> dependencies respected
           -> explicit [P] tasks may run in parallel
           -> same-file/dependent work stays sequential
      -> converge -> implement new tasks -> converge
      -> independent review
           -> every finding becomes mandatory tasks
           -> speckit.implement
           -> converge
           -> review
      -> APPROVED with zero findings
```

PowerPack deliberately does not implement a second task scheduler. `plan.md`, `tasks.md` and upstream `speckit.implement` remain the implementation execution authority.

Every independent-review finding is mandatory current-delivery work, including suggestions, nits, warnings, hardening and documentation findings. Findings may not be deferred. Remediation must synchronize implementation/tests, project documentation and affected active SPEC artifacts.

## Script-runtime parity

Both public commands ship Bash, PowerShell and Python launchers using the same `scripts:` frontmatter mechanism as Spec Kit core commands. Spec Kit resolves `{SCRIPT}` according to the project's `.specify/init-options.json` selection: `sh`, `ps`, or `py`.

The custom `powerpack-control` workflow step is Python because workflow steps execute inside the Spec Kit Python engine; it is not a project shell helper.

## Documentation

- [Installation and usage](docs/INSTALLATION_AND_USAGE.md)
- [Doctor](docs/DOCTOR.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation execution](docs/IMPLEMENTATION_EXECUTION.md)
- [Mid-flight adoption](docs/MIDFLIGHT_ADOPTION.md)
- [Checklist convergence](docs/CHECKLIST_CONVERGENCE.md)
- [Delivery workflow](docs/DELIVERY_WORKFLOW.md)
- [Script runtime](docs/SCRIPT_RUNTIME.md)
- [Independent review](docs/REVIEW.md)
- [Migration](docs/MIGRATION.md)
