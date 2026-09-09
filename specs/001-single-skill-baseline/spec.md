# SPEC-001 — Single Skill Baseline

## Status

Draft

## Summary

Simplify Specify PowerPack to a minimal supported baseline by removing every currently distributed skill except `implement-review`.

The removal is intentionally complete: implementation, registration, discovery, installers, current-state documentation, fixtures, automated tests, and smoke/homologation coverage must all converge on the same product contract.

After this SPEC is implemented, `implement-review` must be the only skill distributed and supported by Specify PowerPack.

## Context

Specify PowerPack is a personal project in continuous evolution. The project is intentionally being refined toward a reusable plugin that can operate across different domains and project contexts.

During this evolution, several skills and capabilities were created or planned while the architecture, lifecycle, ownership model, installation strategy, and agent integrations were still being explored.

Keeping multiple skills active while those foundations are being consolidated increases maintenance surface, installer complexity, smoke-test cost, hidden contracts, and the risk that historical experimentation is interpreted as current product scope.

This SPEC deliberately reduces the functional surface to one proven capability: `implement-review`.

This cleanup is a scope decision, not a declaration that every removed capability was defective. Removed capabilities may be redesigned and reintroduced later through new SPECs.

## Goal

Establish a baseline in which:

> `implement-review` is the only skill implemented, registered, installed, documented as current, discovered, and validated by Specify PowerPack.

The core invariant is:

```text
implemented_skills
== registered_skills
== installed_skills
== documented_current_skills
== smoke_test_expected_skills
== {"implement-review"}
```

## Non-Goals

This SPEC does not:

- redesign `implement-review`;
- add new functionality to `implement-review`;
- replace removed skills with alternative implementations;
- preserve removed skills behind aliases, deprecated commands, hidden flags, or compatibility shims;
- introduce new skills;
- remove generic infrastructure still required by `implement-review` or the PowerPack core;
- convert removed capabilities into bugs or defects retroactively.

## Repository Baseline

Implementation of this SPEC must start from an explicit repository commit.

For the current planning cycle, the baseline repository commit is:

```text
a825557a0d021e9e9948ad212349bf91d76a619c
```

Commit message:

```text
Merge pull request #9 from ds1david/feat/browserless-codereview-stable
feat(review): stabilize browserless Project + GitHub code review
```

The implementation plan must record the actual starting SHA if work begins from a later commit and must explain any resulting inventory differences.

## Related Pull Request

This SPEC is introduced through PR #10:

```text
https://github.com/ds1david/specify-powerpack/pull/10
```

PR #10 also formalizes the project-evolution and defect-versus-capability policy. That policy is relevant to this SPEC because removing a capability from the current product baseline is a deliberate scope decision; historical or planned capability is not automatically a current-contract requirement.

## Definitions

### Preserved skill

The only skill that remains part of the distribution:

```text
implement-review
```

### Removed skill

Any skill present in the repository or generated distribution at the implementation baseline that is not `implement-review`.

The real repository inventory is the source of truth. The implementation must not depend solely on a manually maintained list of skill names.

## Functional Requirements

### FR-001 — Preserve `implement-review`

The project MUST preserve `implement-review`, including every core integration required for it to remain installable, discoverable, and operational.

Its existing behavior MUST NOT change except where a dependency must be adjusted because another skill is being removed.

### FR-002 — Inventory before deletion

Before deleting skill-specific files, implementation MUST inventory all skills present in the baseline repository and identify, for each skill:

- implementation location;
- registration/discovery mechanism;
- installer integration;
- documentation references;
- tests and fixtures;
- shared dependencies;
- final decision: `PRESERVE` or `REMOVE`.

Only `implement-review` may receive `PRESERVE`.

### FR-003 — Remove every other skill

All skills other than `implement-review` MUST be removed.

Removal MUST include, where applicable:

- implementation;
- prompts;
- templates;
- manifests;
- metadata;
- command registrations;
- registries;
- skill-specific configuration;
- scripts;
- assets;
- fixtures;
- dedicated tests;
- operational documentation.

### FR-004 — No runtime discoverability

No removed skill MAY remain discoverable after implementation.

Any registry, manifest, filesystem scan, metadata scan, command generator, or equivalent discovery mechanism MUST expose only `implement-review` among PowerPack-provided skills.

### FR-005 — Update installers

All officially supported installation mechanisms MUST install only `implement-review` as skill content.

The implementation MUST review all applicable entrypoints, including Linux/WSL, Windows, Python, shell, PowerShell, package-based installation, local development installation, and agent-specific installation paths.

No installer MAY copy, register, generate, or reference a removed skill.

### FR-006 — Clean installation contract

A fresh installation into a clean target MUST result in exactly one PowerPack skill:

```text
{"implement-review"}
```

No residual file belonging exclusively to a removed skill MAY be present in the generated installation state.

### FR-007 — Update current-state documentation

README, installation documentation, architecture documentation, usage guides, examples, compatibility material, agent instructions, and other current-state documentation MUST reflect the single-skill baseline.

Documentation MUST clearly distinguish current capabilities from future or historical capabilities.

### FR-008 — Preserve legitimate history

Historical references MAY remain in changelogs, completed SPECs, ADRs, merged-PR history, or other records where removal would destroy useful historical context.

Such references MUST NOT imply that the removed skill is currently available or supported.

### FR-009 — Remove obsolete tests and fixtures

Tests and fixtures whose only purpose is to validate a removed skill MUST be deleted.

Shared helpers MUST be retained only when they remain necessary for `implement-review`, core installation, or generic framework behavior.

### FR-010 — Update smoke tests

Smoke/homologation tests MUST validate at minimum:

1. successful clean installation;
2. discovery of `implement-review`;
3. exact absence of every additional PowerPack skill;
4. absence of residual removed-skill artifacts;
5. minimum operational flow for `implement-review`;
6. consistency across supported operating-system/install paths.

### FR-011 — Exact-set negative assertion

Smoke tests MUST assert equality, not mere presence.

Required semantic contract:

```text
assert discovered_skills == {"implement-review"}
assert installed_skills == {"implement-review"}
```

A test such as the following is insufficient:

```text
assert "implement-review" in discovered_skills
```

### FR-012 — Remove stale configuration

Feature flags, aliases, mappings, constants, paths, environment variables, config keys, registry entries, templates, and other configuration elements used exclusively by removed skills MUST be removed.

### FR-013 — Preserve shared core infrastructure

Generic infrastructure MUST remain when required by `implement-review`, the installation lifecycle, cross-agent support, common tests, or the reusable PowerPack core.

Skill removal MUST NOT become an accidental core redesign.

### FR-014 — No compatibility shims

Removed skills MUST NOT survive through deprecated aliases, redirects, hidden copies, fallback implementations, or compatibility wrappers.

A removed skill is no longer part of the product.

### FR-015 — Removed skill behaves as nonexistent

Where technically applicable, direct invocation of a removed skill name MUST behave as invocation of an unknown/nonexistent skill.

The system MUST NOT silently redirect the invocation to `implement-review` or another capability.

## Installer Contract

All supported installation paths must converge on this logical state:

```text
Specify PowerPack
├── core infrastructure
└── skills
    └── implement-review
```

A platform-specific installer MAY differ internally but MUST NOT produce a different skill inventory.

## Smoke Test Scenarios

### Scenario 1 — Clean installation

**Given** a target without a previous PowerPack installation  
**When** an officially supported installer runs  
**Then** installation succeeds.

### Scenario 2 — Preserved skill exists

**Given** a clean installation  
**When** PowerPack skills are enumerated  
**Then** `implement-review` exists.

### Scenario 3 — Exactly one PowerPack skill

**Given** a clean installation  
**When** PowerPack-provided skills are enumerated  
**Then** the set is exactly `{"implement-review"}`.

### Scenario 4 — Removed skills leave no active residue

**Given** a completed installation  
**When** installed directories, registries, manifests, generated commands, and metadata are inspected  
**Then** no removed skill is present.

### Scenario 5 — `implement-review` remains operational

**Given** a completed installation  
**When** the minimum supported `implement-review` flow is executed  
**Then** the skill remains functional.

### Scenario 6 — Cross-platform consistency

**Given** each supported operating-system/install path  
**When** installation and smoke validation are executed  
**Then** each produces the same PowerPack skill set: `{"implement-review"}`.

## Repository Verification

After removal, implementation MUST perform a repository-wide search for every removed skill name.

Every remaining occurrence must be classified as one of:

```text
ACTIVE_REFERENCE
HISTORICAL_REFERENCE
FALSE_POSITIVE
```

For every removed skill:

```text
ACTIVE_REFERENCE == 0
```

Historical references are allowed only when they preserve meaningful project history and do not advertise current support.

## Regression Guard

At least one automated test MUST make the single-skill baseline an explicit contract:

```text
expected_skills = {"implement-review"}
assert installed_skills == expected_skills
assert registered_skills == expected_skills
```

A future skill must therefore require an intentional change to this contract through a new SPEC or equivalent explicit scope decision.

## Acceptance Criteria

- [ ] Implementation baseline commit is recorded.
- [ ] Complete skill inventory is produced before deletion.
- [ ] `implement-review` is the only skill marked `PRESERVE`.
- [ ] Every other skill implementation is removed.
- [ ] Removed skills have no active runtime registration or discovery path.
- [ ] Removed skills have no active installer integration.
- [ ] Removed-skill-only configuration is removed.
- [ ] Obsolete tests and fixtures are removed.
- [ ] Shared core infrastructure required by `implement-review` remains intact.
- [ ] Linux/WSL installation is validated when supported.
- [ ] Windows installation is validated when supported.
- [ ] A clean installation contains exactly `implement-review`.
- [ ] Smoke tests assert exact-set equality.
- [ ] `implement-review` minimum operational smoke test passes.
- [ ] README and current-state documentation reflect the baseline.
- [ ] Examples do not advertise removed skills as current capabilities.
- [ ] Repository-wide search reports zero active references to removed skills.
- [ ] Full automated test suite passes.

## Risks

### R-001 — Hidden installer references

An installer may continue copying legacy content even after registry cleanup.

**Mitigation:** inspect the resulting installation state, not only installer source code.

### R-002 — Stale documentation

A removed skill may remain advertised after code deletion.

**Mitigation:** global reference scan and current-versus-historical classification.

### R-003 — Shared code accidentally removed

A helper used by a removed skill may also be required by `implement-review`.

**Mitigation:** inventory shared dependencies before deletion.

### R-004 — Weak smoke assertion

Checking only that `implement-review` exists allows legacy skills to remain unnoticed.

**Mitigation:** exact-set assertions.

### R-005 — Platform divergence

Linux/WSL and Windows installers may generate different skill inventories.

**Mitigation:** enforce the same post-install contract on every supported platform.

## Migration Strategy

This change is intentionally breaking for consumers of removed skills.

No deprecation compatibility layer is required.

The migration sequence is:

1. inventory the baseline;
2. identify shared dependencies;
3. remove non-`implement-review` skills;
4. clean registration and configuration;
5. update installers;
6. update documentation;
7. update automated and smoke tests;
8. validate clean installations on supported platforms;
9. run repository-wide residual-reference verification.

Removed capabilities may later return only through explicit new scope decisions compatible with the architecture current at that time.

## Definition of Done

This SPEC is complete when every officially supported installation path results in:

```text
Specify PowerPack
└── skills
    └── implement-review
```

and when implementation, registration, installation, current-state documentation, and smoke-test expectations all describe that same state.
