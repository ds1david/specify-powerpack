# SPEC-011 — Cross-Platform Installation and Managed Updates

**Status:** IMPLEMENTED

## Goal
Install, bootstrap and update Specify PowerPack consistently on Linux/WSL/macOS and Windows while preserving project configuration unless reset is explicit.

## Requirements
- FR-011-01 Canonical CLI MUST be `specify-powerpack`; `speckit-powerpack` remains a migration alias.
- FR-011-02 Installer MUST support Python 3.11+ and uv bootstrap.
- FR-011-03 Official Spec Kit MUST remain a prerequisite and MAY be bootstrapped.
- FR-011-04 Updates MUST preserve project configuration unless reset is explicitly requested.

## Success criteria
Linux/WSL and Windows reach equivalent installed state, source/ref is diagnosable, configuration reset is explicit, and Spec Kit compatibility is checked.