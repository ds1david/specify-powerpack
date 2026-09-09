# SPEC-007 — Browserless ChatGPT Project Context

**Status:** IMPLEMENTED

## Goal
Read the selected ChatGPT Project as account-scoped read-only context using Codex-authenticated platform services without browser automation.

## Requirements
- FR-007-01 Supported path MUST NOT require Chrome, Playwright, Selenium, CDP or Web2API.
- FR-007-02 Project binding MUST be explicit and repository-scoped.
- FR-007-03 Project context MUST be reported as serialized context, not native conversation binding.
- FR-007-04 Provider unavailability MUST fail closed.

## Success criteria
No browser dependency exists in the supported path, missing/wrong binding blocks Project-aware review, and context identity is observable without claiming response persistence in ChatGPT Project.