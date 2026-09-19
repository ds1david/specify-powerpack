# SPEC-001 - PowerPack Delivery

## Functional requirements

- FR-001 expose only speckit.powerpack.deliver as the initial public PowerPack command.
- FR-002 delegate lifecycle orchestration to workflow powerpack-delivery.
- FR-003 support new features and deterministic mid-flight adoption.
- FR-004 follow Spec Kit feature-directory authority before textual target heuristics.
- FR-005 preserve completed upstream artifacts during adoption.
- FR-006 converge existing reviewer-owned checklists before implementation without bulk approval or user bypass.
- FR-007 treat analyze as advisory and read-only; do not route backward by parsing its prose.
- FR-008 compose upstream implement/converge and repeat when converge changes tasks.md.
- FR-009 support adoption after partial implementation and prior PowerPack review attempts.
- FR-010 run independent code review only against an exact committed and pushed PR HEAD.
- FR-011 return every review finding to mandatory remediation, then re-converge before re-review.
- FR-012 never convert BLOCKED or loop-budget exhaustion to approval.
- FR-013 honor Spec Kit selected sh/ps/py script runtime for public command helpers.
- FR-014 active runtime must have no dependency on the archived pre-rewrite tree.
- FR-015 document architecture, adoption, checklist convergence, workflow, runtime, review and migration boundaries.

## Acceptance scenario: manual through analyze

Given .specify/feature.json points to specs/soak/003-soak-qualification, and spec/plan/tasks plus a custom checklist already exist, when speckit.powerpack.deliver spec-soak-003 is invoked, PowerPack preserves prior SDD artifacts, converges unchecked checklist criteria, reruns analyze as a freshness report, implements pending tasks, converges implementation and performs independent review.
