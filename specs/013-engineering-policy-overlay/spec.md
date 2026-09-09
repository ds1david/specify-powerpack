# SPEC-013 — Engineering Policy Overlay

**Status:** PLANNED

## Goal
Apply reusable engineering rules across languages/frameworks while preserving project constitution and existing architecture as higher-authority context.

## Requirements
- FR-013-01 Project constitution/rules MUST remain authoritative.
- FR-013-02 Policies MUST compose across language, version, runtime, framework, architecture, app type and domain axes.
- FR-013-03 Rules MUST have stable IDs and MUST/SHOULD/MAY severity.
- FR-013-04 Implementation and review MUST consume the same effective policy set.
- FR-013-05 Conflicts and de-duplication MUST be deterministic and inspectable.

## Success criteria
Existing project rules are not overwritten, conflicts are visible, Java/Python/frontend profiles are version-aware, and agents do not silently transform architecture.