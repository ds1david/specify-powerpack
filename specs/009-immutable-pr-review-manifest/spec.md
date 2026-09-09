# SPEC-009 — Immutable PR Review Manifest

**Status:** IMPLEMENTED

## Goal
Bind review to the exact PR base, merge-base, head, changed-file set, active SPEC and deterministic snapshot digest before deep review begins.

## Requirements
- FR-009-01 Manifest MUST include PR identity, base ref/SHA, merge-base, head SHA and changed files.
- FR-009-02 Local HEAD MUST equal PR head for final review.
- FR-009-03 Exactly one active SPEC MUST resolve.
- FR-009-04 Any snapshot change MUST invalidate prior review evidence.

## Success criteria
Stale HEAD and ambiguous SPEC block review, changed-file coverage is exact, and approval cannot be reused after snapshot mutation.