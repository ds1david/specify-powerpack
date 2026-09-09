# SPEC-008 — GitHub App Review Transport

**Status:** IMPLEMENTED

## Goal
Use the official Codex Apps MCP runtime and an explicitly selected GitHub connector to obtain authoritative PR/diff/file evidence for review.

## Requirements
- FR-008-01 Authoritative GitHub review evidence MUST come from GitHub tool calls/results.
- FR-008-02 Shell and web-search fallback MUST be rejected for authoritative PR evidence.
- FR-008-03 Connector identity MUST be explicit.
- FR-008-04 Review transport MUST remain read-only.

## Success criteria
Unavailable connector blocks review, codex_apps tool evidence is structurally verified, and no merge/approval/destructive Git operation is authorized.