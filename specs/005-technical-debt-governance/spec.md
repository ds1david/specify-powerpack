# SPEC-005 — Technical Debt Governance

**Status:** IMPLEMENTED

## Goal
Prevent current-scope defects, review findings and convergence gaps from being relabeled as technical debt merely to force workflow completion.

## Requirements
- FR-005-01 Active-SPEC requirements MUST NOT be deferred as debt.
- FR-005-02 Open implement-review findings MUST NOT be converted to debt.
- FR-005-03 Open convergence gaps MUST NOT be converted to debt.
- FR-005-04 P0/BLOCKER correctness or security issues MUST NOT be ordinary debt.

## Success criteria
Invalid debt is rejected with rationale while legitimate out-of-scope improvements remain recordable and auditable.