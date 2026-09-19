# PowerPack Deep Review Protocol

Authority order:
1. immutable Pull Request evidence;
2. constitution, architecture and explicit durable contracts;
3. active SPEC artifacts;
4. implementation;
5. tests as evidence, never authority;
6. previous review only for finding revalidation.

Mandatory fronts:
1. SPEC_COMPLIANCE
2. BEHAVIORAL_REGRESSION
3. ARCHITECTURE_AND_CONTRACTS
4. STATE_CONCURRENCY_AND_FAILURES
5. PERSISTENCE_DETERMINISM_IDEMPOTENCY
6. TESTS_AND_COMPOSITION_ROOT
7. DOCUMENTATION_AND_OPERABILITY
8. SECURITY_AND_SCOPE

NOT_APPLICABLE requires evidence. Do not stop at the first blocker. Inspect every changed file, complete every front, and perform a second systematic pass.

APPROVED requires zero findings, complete changed-file and requirement coverage, no material context gaps, mandatory-front completion, and a survived adversarial verdict challenge.
