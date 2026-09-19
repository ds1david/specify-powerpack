---
description: Validate the local Spec Kit and Specify PowerPack installation, review prerequisites, runtime selection, and active feature state.
scripts:
  sh: ../../scripts/bash/doctor.sh
  ps: ../../scripts/powershell/doctor.ps1
  py: ../../scripts/python/doctor.py
---

## User Input

$ARGUMENTS

Run {SCRIPT} once from the repository root, passing the exact user input.

By default the doctor performs local checks plus the GitHub App connectivity check required by independent review. Use `--offline` only when network validation is intentionally unavailable. Use `--json` for machine-readable output.

The doctor is diagnostic and read-only. It must not install, repair, rewrite, commit, push, mutate a Pull Request, or change checklist/review state.
