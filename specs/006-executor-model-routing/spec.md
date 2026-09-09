# SPEC-006 — Executor and Model Routing

**Status:** IMPLEMENTED

## Goal
Route workflow execution and review across supported agent CLIs while keeping executor choice explicit and separate from review policy.

## Requirements
- FR-006-01 Executor selection MUST be explicit and inspectable.
- FR-006-02 Routing MUST NOT silently cross providers.
- FR-006-03 Model/reasoning settings MUST be configuration, not workflow semantics.
- FR-006-04 Unsupported integrations MUST fail clearly.

## Success criteria
Active executor is visible, unsupported values do not silently fall back, and reviewer transport remains independently configurable.