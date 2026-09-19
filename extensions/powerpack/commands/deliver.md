---
description: Start or adopt a Spec Kit feature and drive the remaining lifecycle through checklist, phase-aware implementation and independent-review convergence.
scripts:
  sh: ../../scripts/bash/deliver.sh
  ps: ../../scripts/powershell/deliver.ps1
  py: ../../scripts/python/deliver.py
---

## User Input

$ARGUMENTS

Run {SCRIPT} once from the repository root, passing the exact user input as the target.

The launcher starts the installed powerpack-delivery workflow and forwards the script runtime selected by Spec Kit. Do not manually reproduce, reorder, or skip workflow phases.

Adoption and implementation rules:

- follow Spec Kit active-feature authority (SPECIFY_FEATURE_DIRECTORY and .specify/feature.json) before interpreting the textual target;
- preserve valid existing SPEC artifacts and completed task markers;
- never regenerate a completed SDD phase merely because it was executed manually;
- converge existing reviewer-owned checklists before implementation; never bypass their gate and never approve items in bulk;
- re-run speckit.analyze as an advisory freshness pass when tasks exist; do not parse its prose to automatically jump backward;
- treat plan.md and tasks.md as the implementation execution authority;
- execute implementation only through speckit.implement so its phase-by-phase, dependency, TDD, same-file serialization and [P] scheduling rules remain authoritative;
- never invent parallelism: only tasks explicitly marked [P] by tasks.md are parallel candidates, and same-file/dependency-related work remains sequential;
- let speckit.converge drive durable implementation reconciliation by appending tasks, then execute the resulting tasks through speckit.implement under the same phase/[P] rules;
- materialize every review finding into dependency-correct remediation tasks before implementation;
- treat every independent-review finding as mandatory current-delivery work;
- never convert BLOCKED or exhausted convergence budgets into success.
