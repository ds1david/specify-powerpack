# SPEC-001 - PowerPack Delivery

## Functional requirements

- FR-001 expose exactly two public PowerPack commands: `speckit.powerpack.deliver` for delivery and `speckit.powerpack.doctor` for read-only diagnostics.
- FR-002 delegate lifecycle orchestration to workflow `powerpack-delivery`.
- FR-003 support new features and deterministic mid-flight adoption.
- FR-004 follow Spec Kit feature-directory authority before textual target heuristics.
- FR-005 preserve completed upstream artifacts during adoption.
- FR-006 converge existing reviewer-owned checklists before implementation without bulk approval or user bypass.
- FR-007 treat analyze as advisory and read-only; do not route backward by parsing its prose.
- FR-008 compose upstream implement/converge and repeat when converge changes `tasks.md`.
- FR-009 support adoption after partial implementation and prior PowerPack review attempts.
- FR-010 run independent code review only against an exact committed and pushed PR HEAD.
- FR-011 treat every valid emitted review finding as mandatory current-delivery work regardless of severity/category/wording, including suggestions, nits, warnings, hardening and documentation findings; no finding may be deferred.
- FR-012 every review remediation MUST update implementation/tests as applicable, project documentation for affected behavior/operation, and active SPEC artifacts for affected requirements/contracts/acceptance criteria/invariants/tasks before re-convergence and re-review.
- FR-013 never convert BLOCKED or loop-budget exhaustion to approval.
- FR-014 honor Spec Kit selected sh/ps/py script runtime for both public command helpers.
- FR-015 active runtime must have no dependency on the archived pre-rewrite tree.
- FR-016 provide `speckit.powerpack.doctor` as a workflow-independent, read-only diagnostic that validates Spec Kit compatibility, runtime/integration selection, installed PowerPack extension/workflow/step, Git/Codex/GitHub review prerequisites and active feature state.
- FR-017 doctor MUST fail closed for missing/stale required PowerPack components or review prerequisites, while treating a dirty working tree and incomplete but valid mid-flight feature artifacts as warnings rather than installation failures.
- FR-018 document installation, usage, architecture, adoption, checklist convergence, workflow, runtime, review, doctor and migration boundaries.
- FR-019 publish the `powerpack-control` step through a narrow PowerPack-owned step catalog so current Spec Kit can install the custom step without depending on the archived implementation.

## Acceptance scenario: manual through analyze

Given `.specify/feature.json` points to `specs/soak/003-soak-qualification`, and spec/plan/tasks plus a custom checklist already exist, when `speckit.powerpack.deliver spec-soak-003` is invoked, PowerPack preserves prior SDD artifacts, converges unchecked checklist criteria, reruns analyze as a freshness report, implements pending tasks, converges implementation and performs independent review.

## Acceptance scenario: review suggestion

Given independent review emits a valid finding labelled as a suggestion or low-severity improvement with a current authority reference, when PowerPack handles `CHANGES_REQUIRED`, then the finding is implemented in the current delivery, relevant tests are updated, affected project documentation and active SPEC artifacts are synchronized, convergence runs again and the PR is re-reviewed. The finding is not deferred or treated as optional.

## Acceptance scenario: doctor

Given PowerPack is installed in an initialized Spec Kit project, when `speckit.powerpack.doctor` runs, then it validates the selected script runtime, active integration, extension/workflow/custom-step installation, Git/Codex/GitHub review prerequisites and active feature state without mutating the project or GitHub. Missing required components cause a non-zero exit.
