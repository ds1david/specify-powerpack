# Specify PowerPack — Spec Registry

This directory is the canonical product backlog for Specify PowerPack itself. The official Spec Kit workflow is mandatory for product evolution:

`speckit-specify → speckit-clarify → speckit-plan → speckit-checklist → speckit-checklist-converge → speckit-tasks → speckit-analyze → speckit-implement → speckit-implement-review`.

Status taxonomy: `IMPLEMENTED` records an already-shipped baseline that future fixes must preserve; `PLANNED` is new capability work that still needs implementation/convergence; `PARTIAL` is allowed only when shipped behavior and missing scope are both explicit.

| SPEC | Capability | Status |
|---|---|---|
| 000 | Bootstrap spec-driven backlog | IMPLEMENTED |
| 001 | Same-SPEC predecessor receipts | IMPLEMENTED |
| 002 | Checklist convergence | IMPLEMENTED |
| 003 | Implementation review convergence | IMPLEMENTED |
| 004 | Capability-based quality gates | IMPLEMENTED |
| 005 | Technical debt governance | IMPLEMENTED |
| 006 | Executor and model routing | IMPLEMENTED |
| 007 | Browserless ChatGPT Project context | IMPLEMENTED |
| 008 | GitHub App review transport | IMPLEMENTED |
| 009 | Immutable PR review manifest | IMPLEMENTED |
| 010 | Full-cycle orchestration | IMPLEMENTED |
| 011 | Cross-platform installation and managed updates | IMPLEMENTED |
| 012 | Provider-neutral review and Copilot modes | PLANNED |
| 013 | Engineering policy overlay | PLANNED |
| 014 | Cross-platform homologation harness | PLANNED |

A bug remains in the owning SPEC. A change that introduces a new capability or changes the contract starts a new SPEC.