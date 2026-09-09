# SPEC-004 — Capability-Based Quality Gates

**Status:** IMPLEMENTED

## Goal
Discover project capabilities and select validation strategies without hard-coding Maven, npm, pytest or any single ecosystem.

## Requirements
- FR-004-01 Detection MUST be capability-driven.
- FR-004-02 A project MAY expose multiple applicable quality gates.
- FR-004-03 Unknown capability MUST be reported rather than guessed.
- FR-004-04 Explicit project configuration MUST override generic defaults.

## Success criteria
Different stacks select appropriate gates without code forks, missing tools are distinguishable from failing checks, and execution evidence is reusable by implement-review.