# Independent review

Independent code review runs only after Spec Kit convergence stabilizes and the feature branch has been committed, pushed and represented by exactly one open Pull Request.

The reviewer must use the configured GitHub App as repository evidence, bind the exact PR head to local full HEAD, cover every changed file and requirement, continue after the first finding, revalidate prior findings and challenge its tentative verdict.

Review outputs are stored under `.specify/powerpack/delivery/reviews/`.

## Zero-finding merge contract

PowerPack does not distinguish “blocking” findings from “optional suggestions” after the independent reviewer emits them. Every emitted finding is mandatory current-delivery work regardless of severity, category or wording, including suggestions, nits, warnings, hardening and documentation findings.

This does not authorize speculative backlog generation: a finding still needs current evidence and an authority reference. But once the reviewer emits a valid finding, it cannot be ignored, downgraded to advisory work, deferred to technical debt, converted into a TODO or moved to a future SPEC.

For every finding, remediation must synchronize all affected surfaces:

1. implementation/configuration;
2. tests and verification evidence;
3. project documentation describing the affected behavior, architecture or operation;
4. active SPEC artifacts when the finding changes or clarifies a requirement, contract, acceptance criterion, invariant, task or documented delivery decision.

After remediation, Spec Kit `converge` runs again, the exact PR HEAD is republished and independent review runs again.

`CHANGES_REQUIRED` is mandatory work. `BLOCKED` never becomes approval. `APPROVED` requires zero findings.
