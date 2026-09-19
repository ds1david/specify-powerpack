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
- FR-018 document installation, usage, architecture, adoption, checklist convergence, implementation execution, workflow, runtime, review, doctor and migration boundaries.
- FR-019 publish the `powerpack-control` step through a narrow PowerPack-owned step catalog so current Spec Kit can install the custom step without depending on the archived implementation.
- FR-020 treat `plan.md` and `tasks.md` as the implementation execution authority and validate task phase structure before and after every implementation invocation.
- FR-021 execute implementation work only through upstream `speckit.implement` for initial implementation, mid-flight continuation, convergence tasks and review-remediation tasks.
- FR-022 preserve the phase order and dependency graph defined by `tasks.md`; a later phase MUST NOT be accepted as started while an earlier phase still has pending tasks.
- FR-023 permit task-level parallel execution only for explicit `[P]` tasks and never infer additional parallelism. Same-file or dependency-related work MUST remain sequential.
- FR-024 review remediation MUST first materialize every finding as dependency-correct tasks, including implementation/configuration, tests/verification and project-documentation work as applicable, then execute those tasks through `speckit.implement`.
- FR-025 publish release assets whose archive roots are directly consumable by Spec Kit `extension add --from` and `workflow add --from`; normal installation documentation MUST prefer immutable release assets over local `--dev` installation.

## Acceptance scenario: manual through analyze

Given `.specify/feature.json` points to `specs/soak/003-soak-qualification`, and spec/plan/tasks plus a custom checklist already exist, when `speckit.powerpack.deliver spec-soak-003` is invoked, PowerPack preserves prior SDD artifacts, converges unchecked checklist criteria, reruns analyze as a freshness report, validates the implementation task plan, implements pending tasks phase-by-phase, converges implementation and performs independent review.

## Acceptance scenario: explicit parallel work

Given the current pending task phase contains independent tasks explicitly marked `[P]` and sequential tasks without `[P]`, when PowerPack invokes implementation, then it delegates to `speckit.implement`; only the explicit `[P]` tasks are candidates for parallel execution and dependency/same-file work remains sequential.

## Acceptance scenario: review suggestion

Given independent review emits a valid finding labelled as a suggestion or low-severity improvement with a current authority reference, when PowerPack handles `CHANGES_REQUIRED`, then the finding is first added to active SPEC traceability and dependency-correct remediation tasks, those tasks are executed by `speckit.implement`, project documentation is updated, convergence runs again and the PR is re-reviewed. The finding is not deferred or treated as optional.

## Acceptance scenario: doctor

Given PowerPack is installed in an initialized Spec Kit project with a valid `tasks.md`, when `speckit.powerpack.doctor` runs, then it reports the current task phase and pending `[P]` opportunities in addition to installation/runtime/review checks, without mutating the project or GitHub.

## Acceptance scenario: release installation

Given a published PowerPack version `vX.Y.Z`, when a consumer installs the extension and workflow using their versioned release asset URLs with `--from`, then Spec Kit finds `extension.yml` and `workflow.yml` at each archive root and installs without requiring a PowerPack repository checkout.
