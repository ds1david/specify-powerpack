---
description: Start or adopt a Spec Kit feature and drive the remaining lifecycle through checklist, implementation and independent-review convergence.
scripts:
  sh: ../../scripts/bash/deliver.sh
  ps: ../../scripts/powershell/deliver.ps1
  py: ../../scripts/python/deliver.py
---

## User Input

$ARGUMENTS

Run {SCRIPT} once from the repository root, passing the exact user input as the target.

The launcher starts the installed powerpack-delivery workflow and forwards the script runtime selected by Spec Kit. Do not manually reproduce, reorder, or skip workflow phases.

Adoption rules:

- follow Spec Kit active-feature authority (SPECIFY_FEATURE_DIRECTORY and .specify/feature.json) before interpreting the textual target;
- preserve valid existing SPEC artifacts and completed task markers;
- never regenerate a completed phase merely because it was executed manually;
- converge existing reviewer-owned checklists before implementation; never bypass their gate and never approve items in bulk;
- re-run speckit.analyze as an advisory freshness pass when tasks exist; do not parse its prose to automatically jump backward;
- let speckit.converge drive durable implementation reconciliation by appending tasks;
- treat every independent-review finding as mandatory current-delivery work;
- never convert BLOCKED or exhausted convergence budgets into success.
