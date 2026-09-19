# Mid-flight adoption

PowerPack can take control of a feature that was started manually.

Feature resolution follows Spec Kit authority:

1. SPECIFY_FEATURE_DIRECTORY
2. .specify/feature.json feature_directory
3. an unambiguous explicit target
4. an unambiguous branch-directory match

The target string is a hint, not stronger authority than Spec Kit's persisted feature directory.

## Example: manual work through analyze

Given an active feature with spec.md, plan.md, reviewer-owned checklists, tasks.md and a previously executed manual speckit.analyze, with no implementation/review yet, PowerPack does not rerun clarify, plan, checklist generation or tasks generation.

It executes:

checklist-converge -> analyze -> implement -> converge ... -> independent review

Analyze is rerun because it is read-only and leaves no durable machine-readable proof of a clean prior run.

If some implementation tasks are already checked, speckit.implement resumes remaining tasks. If all are checked, PowerPack goes directly to converge; converge can append work when code still fails the SPEC.
