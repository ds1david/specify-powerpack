# SPEC-003 — Implementation Review Convergence

**Status:** IMPLEMENTED

## Goal
Own the post-implementation repair loop: quality gates, independent deep review, finding validation, corrective implementation and final approval on the current snapshot.

## Requirements
- FR-003-01 `implement-review` MUST require an explicit same-SPEC implement predecessor.
- FR-003-02 Any code change after review MUST invalidate approvals for the prior snapshot.
- FR-003-03 Findings MUST return to implementation until resolved or blocked.
- FR-003-04 Approval MUST be schema-validated and evidence-backed.

## Success criteria
The command never manufactures initial implementation; unresolved findings cannot disappear into debt; final approval is bound to current snapshot evidence.