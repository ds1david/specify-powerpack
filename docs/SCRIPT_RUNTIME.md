# Script runtime compatibility

Spec Kit persists the project script choice made during initialization in `.specify/init-options.json` as `sh`, `ps` or `py`.

PowerPack uses the same command frontmatter contract for both public commands.

Delivery:

```yaml
scripts:
  sh: ../../scripts/bash/deliver.sh
  ps: ../../scripts/powershell/deliver.ps1
  py: ../../scripts/python/deliver.py
```

Doctor:

```yaml
scripts:
  sh: ../../scripts/bash/doctor.sh
  ps: ../../scripts/powershell/doctor.ps1
  py: ../../scripts/python/doctor.py
```

The command body invokes `{SCRIPT}`. Spec Kit replaces that placeholder with the selected variant when materializing the command or skill for the active integration.

The doctor checks that the launcher runtime matches the persisted Spec Kit selection and fails with a remediation hint when the installed command artifacts are stale.

The custom workflow step is not a project script. Community workflow steps execute inside Spec Kit's Python workflow engine and therefore use Python by design.
