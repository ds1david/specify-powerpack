# SPEC-001 — Same-SPEC Predecessor Receipts

**Status:** IMPLEMENTED

## Goal
Guarantee that workflow predecessor evidence belongs to the active SPEC so later commands cannot infer execution merely from artifacts on disk.

## Requirements
- FR-001-01 Receipts MUST be scoped to one SPEC identity.
- FR-001-02 A phase MUST reject predecessor receipts from another SPEC.
- FR-001-03 Artifact existence alone MUST NOT prove a workflow phase executed.
- FR-001-04 Initial implementation MUST remain explicit.

## Success criteria
Cross-SPEC/stale receipts are rejected, missing predecessors yield an actionable next command, and valid same-SPEC receipts permit progression.