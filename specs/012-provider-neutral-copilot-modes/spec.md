# SPEC-012 — Provider-Neutral Review and Copilot Modes

**Status:** PLANNED

## Goal
Generalize execution/review boundaries so PowerPack supports isolated single-provider mode and explicit cross-agent mode, including Copilot-only and Copilot+Codex paths.

## Requirements
- FR-012-01 Single-provider mode MUST NOT cross into another CLI/provider.
- FR-012-02 Copilot-only MUST NOT require Codex auth or ChatGPT Project binding.
- FR-012-03 Cross-agent mode MUST expose the reviewer boundary explicitly.
- FR-012-04 Review protocol MUST be provider-neutral and transports MUST implement a common contract.
- FR-012-05 Provider unavailability MUST NOT become implicit approval.

## Success criteria
Copilot-only passes with Codex unavailable; Copilot+Codex reports cross-agent review; Project binding is N/A in isolated Copilot mode; provider failures fail closed.