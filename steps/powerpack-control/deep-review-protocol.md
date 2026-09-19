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

A finding still requires concrete current evidence and a current authority reference. Do not invent speculative backlog work. However, do not suppress an evidence-backed current issue because its severity is low or because it would normally be described as a suggestion, nit, hardening item or documentation improvement. Under PowerPack every emitted finding is mandatory current-delivery work and therefore prevents APPROVED until remediated.

APPROVED requires zero findings, complete changed-file and requirement coverage, no material context gaps, mandatory-front completion, and a survived adversarial verdict challenge.
