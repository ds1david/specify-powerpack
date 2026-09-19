# Independent review

Independent code review runs only after Spec Kit convergence stabilizes and the feature branch has been committed, pushed and represented by exactly one open Pull Request.

The reviewer must use the configured GitHub App as repository evidence, bind the exact PR head to local full HEAD, cover every changed file and requirement, continue after the first finding, revalidate prior findings and challenge its tentative verdict.

Review outputs are stored under `.specify/powerpack/delivery/reviews/`.

## Zero-finding merge contract

Every emitted valid finding is mandatory current-delivery work regardless of severity, category or wording, including suggestions, nits, warnings, hardening and documentation findings.

A finding still needs current evidence and an authority reference. PowerPack does not authorize speculative backlog generation.

## Remediation execution

The remediation agent does not directly patch product code as an ad-hoc shortcut. It first updates active SPEC traceability as required and materializes each finding as explicit tasks in `tasks.md`.

Those tasks must respect `plan.md`, existing phase order and dependency edges. `[P]` may be added only for independent, different-file work with no incomplete dependency.

The resulting remediation is executed by `speckit.implement`, exactly like initial implementation and convergence tasks. Therefore phase ordering, TDD ordering, same-file serialization, task completion markers and declared parallel opportunities use one common executor.

After remediation, Spec Kit `converge` runs again, the exact PR HEAD is republished and independent review runs again.

`BLOCKED` never becomes approval. `APPROVED` requires zero findings.
