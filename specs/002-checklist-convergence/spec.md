# SPEC-002 — Checklist Convergence

**Status:** IMPLEMENTED

## Goal
Add an active convergence phase after checklist generation so unresolved mandatory gaps are repaired before tasks are considered implementation-ready.

## Requirements
- FR-002-01 Active SPEC and checklist MUST be authoritative.
- FR-002-02 Actionable gaps MUST return to correction rather than silent waiver.
- FR-002-03 Convergence MUST end only when mandatory items pass or are explicitly blocked.
- FR-002-04 The mechanism MUST remain language/framework agnostic.

## Success criteria
Successful convergence produces evidence/receipt; blocked gaps remain visible; mandatory gaps cannot be marked complete without evidence.