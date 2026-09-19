# SPEC-004 — Deterministic Implement Review Acceptance

Normative artifact set:

- `spec.md` — feature contract, delivery-target model, same-SPEC evidence, review classifications and completion semantics.
- `contracts/rigorous-review-gates.md` — mandatory zero-finding PR-review gates, formal `REQUEST_CHANGES`, no technical-debt escape hatch, and finding-to-artifact materialization.
- `tasks.md` — implementation plan for target resolution, evidence binding, finding normalization, formal GitHub review enforcement and homologation.
- `checklists/requirements.md` — requirements-completeness checklist.
- `checklists/pr-review-gate.md` — operational PR-review gate checklist.

A conforming implementation MUST satisfy `spec.md` and the rigorous-review contract together. The supporting tasks/checklists are intended to make those obligations explicit and regression-testable.
