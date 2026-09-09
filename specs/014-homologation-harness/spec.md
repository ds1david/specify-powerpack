# SPEC-014 — Cross-Platform Homologation Harness

**Status:** PLANNED

## Goal
Automate formal H1-H5 product homologation on Linux/WSL and Windows with reproducible evidence, positive/negative smokes and explicit PASS/FAIL/BLOCKED/SKIPPED states.

## Requirements
- FR-014-01 One Python orchestrator MUST own cross-platform logic; shell/PowerShell MUST be thin wrappers.
- FR-014-02 Harness MUST capture environment, repository snapshot, configuration and smoke evidence.
- FR-014-03 Expected command failure MUST be distinguishable from homologation failure.
- FR-014-04 Secrets/raw auth files MUST NOT be copied into evidence.
- FR-014-05 H1-H5 semantics MUST be equivalent on Linux/WSL and Windows.

## Scenarios
- H1 Codex + Codex review, no Project.
- H2 Codex + Codex/Project review, Project bound.
- H3 Copilot executor + Codex reviewer, no Project.
- H4 Copilot executor + Codex/Project reviewer, Project bound.
- H5 Copilot-only, no Codex/Project dependency.

## Success criteria
All applicable scenarios produce auditable evidence; H5 passes with Codex unavailable; negative smokes are recorded as successful isolation assertions when failure is expected.