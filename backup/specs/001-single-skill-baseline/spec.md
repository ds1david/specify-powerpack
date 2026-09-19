# Feature Specification: Single Skill Baseline

**Feature Branch**: `001-single-skill-baseline`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "001" (feature 001 — regenerate the single-skill cleanup baseline spec on the standard Spec Kit template and reconcile skill/command terminology)

## Overview

Reduce Specify PowerPack to a minimal supported baseline in which `implement-review` is
the only capability that PowerPack implements, registers, installs, documents as current,
exposes for discovery, and validates.

The reduction must be complete and consistent: implementation, preset registration,
discovery, installers, current-state documentation, fixtures, automated tests, and
smoke/homologation coverage must all describe the same product contract.

This is a deliberate scope decision, not a statement that any removed capability was
defective. Removed capabilities may be redesigned and reintroduced later through new specs.

## Terminology *(reconciliation — mandatory reading)*

The previous draft of this spec used the word "skill" throughout. The repository does not
ship "skills"; it ships **PowerPack-provided preset commands** through the `powerpack-core`
preset (`src/speckit_powerpack/assets/presets/powerpack-core/preset.yml`, entries under
`provides.templates` with `type: "command"`). This spec uses these terms precisely:

- **PowerPack-provided command**: a command template registered by the `powerpack-core`
  preset. At the baseline these are: `speckit.implement`, `speckit.converge`,
  `speckit.checklist-converge`, `speckit.implement-review`, `speckit.full-cycle`,
  `speckit.debt-create`, `speckit.debt-list`, `speckit.debt-consult`, `speckit.debt-start`,
  `speckit.debt-close`.
- **Preserved capability**: `implement-review` (the `speckit.implement-review` command plus
  every supporting asset, runtime, and integration it needs to remain installable,
  discoverable, and operational).
- **Removed command**: any PowerPack-provided command in the baseline preset that is not
  `speckit.implement-review`, unless a `[NEEDS CLARIFICATION]` resolution below explicitly
  preserves it as a required dependency of `implement-review`.
- **Out of scope for removal**: the upstream Spec Kit workflow commands / agent skills
  (`speckit-plan`, `speckit-tasks`, `speckit-specify`, `speckit-analyze`, `speckit-clarify`,
  `speckit-constitution`, `speckit-checklist`, `speckit-converge`, `speckit-implement`,
  `speckit-taskstoissues`, `graphify`, …) that PowerPack does not own. They live under the
  host project's `.claude/skills/` and are installed by Spec Kit / other tooling, not by
  PowerPack. Nothing in this spec deletes or renames them.

The exact-set assertions in this spec are always scoped to **PowerPack-provided commands**,
never to the host project's full command or skill inventory.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A clean install exposes only `implement-review` (Priority: P1)

A maintainer installs Specify PowerPack into a clean, Spec Kit-initialized project on a
supported platform. After installation, the only PowerPack-provided command available is
`speckit.implement-review`. No removed command is registered, generated, discoverable, or
left on disk as a PowerPack artifact.

**Why this priority**: This is the entire point of the baseline. If a clean install still
surfaces legacy commands, the cleanup has failed regardless of what the source tree looks
like.

**Independent Test**: Run each officially supported installer against a fresh target,
enumerate PowerPack-provided commands from the installed preset/registry, and assert the
set equals `{"speckit.implement-review"}`. Inspect the install tree for residual
removed-command assets and assert none exist.

**Acceptance Scenarios**:

1. **Given** a Spec Kit project with no prior PowerPack installation, **When** a supported
   installer runs to completion, **Then** installation succeeds with no error.
2. **Given** a completed clean installation, **When** PowerPack-provided commands are
   enumerated, **Then** the set is exactly `{"speckit.implement-review"}`.
3. **Given** a completed clean installation, **When** the installed directories, preset
   registration, generated command files, and PowerPack metadata are inspected, **Then**
   no asset belonging exclusively to a removed command is present.

### User Story 2 - `implement-review` still works end to end (Priority: P1)

After the cleanup, a maintainer runs the minimum supported `implement-review` flow on a
project that has an explicit completed implementation. The flow reaches its normal
terminal state (convergence + quality gate + independent review) without being blocked by
a missing PowerPack dependency.

**Why this priority**: The baseline is worthless if the one preserved capability is broken
by the removal of a command or runtime helper it silently depended on.

**Independent Test**: On a fixture project with a recorded completed implementation,
execute the documented minimum `implement-review` path and assert it completes (or blocks
only for legitimate configuration reasons unrelated to the removed commands).

**Acceptance Scenarios**:

1. **Given** a clean installation and a project with a valid completed implementation
   receipt, **When** the `implement-review` prerequisite check runs, **Then** it passes.
2. **Given** the `implement-review` flow is executing, **When** it needs to converge or
   re-run implementation for authorized appended work, **Then** the mechanism it depends on
   for that step is still present and functional.
3. **Given** the mandatory readiness checks for `implement-review`, **When** they run,
   **Then** every command/runtime they invoke still exists after the cleanup.

### User Story 3 - No removed command survives as a hidden path (Priority: P2)

A maintainer audits the repository and the installed state for every removed command name.
Every remaining occurrence is either legitimate project history or an inert false positive.
Nothing advertises a removed command as currently supported, and invoking a removed command
name behaves like invoking an unknown command — never a silent redirect to `implement-review`.

**Why this priority**: Weak cleanup leaves aliases, shims, or stale docs that re-expand the
supported surface without an explicit decision.

**Independent Test**: Grep the whole repository for each removed command name, classify
every hit, and assert zero active references. Attempt to invoke a removed command name
against a clean install and assert unknown-command behavior.

**Acceptance Scenarios**:

1. **Given** the cleanup is complete, **When** the repository is searched for a removed
   command name, **Then** every hit is classified `HISTORICAL_REFERENCE` or `FALSE_POSITIVE`
   and `ACTIVE_REFERENCE == 0`.
2. **Given** a clean installation, **When** a removed command name is invoked directly,
   **Then** the system reports it as unknown/nonexistent and does not run `implement-review`.
3. **Given** current-state documentation (README, installation, architecture, usage,
   agent instructions), **When** it is reviewed, **Then** it presents only `implement-review`
   as a current PowerPack capability and clearly separates historical/future capabilities.

### User Story 4 - The baseline is guarded against silent regression (Priority: P2)

A contributor later adds a new PowerPack command without an explicit scope decision. An
automated test fails because the single-command baseline is encoded as an exact-set
contract.

**Why this priority**: Without a regression guard, the baseline erodes on the next feature
branch and the cleanup has to be redone.

**Independent Test**: Add a second PowerPack-provided command in a scratch branch and run
the suite; the baseline contract test must fail.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** it runs against the baseline, **Then** at least one
   test asserts `registered PowerPack commands == {"speckit.implement-review"}` as equality,
   not membership.
2. **Given** a change that adds or restores a PowerPack-provided command, **When** the suite
   runs, **Then** the baseline contract test fails until the contract is intentionally updated.

### Edge Cases

- A platform-specific installer (Linux/WSL vs Windows, shell vs PowerShell vs Python vs
  package vs local-dev) copies legacy content even after preset cleanup → the contract is
  verified against the resulting install state, not only installer source.
- A helper or runtime module used by a removed command is also required by `implement-review`
  → it is classified as shared core infrastructure and preserved (see FR-013).
- A removed command name still appears in a completed spec, changelog, ADR, or merged-PR
  record → allowed as `HISTORICAL_REFERENCE` provided it does not imply current support.
- The `implement-review` flow calls `speckit-converge` / `speckit-implement` internally →
  resolution of the dependency clarification below determines whether those remain.
- Smoke test only checks `"speckit.implement-review" in commands` → insufficient; exact-set
  equality is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: PowerPack MUST preserve `implement-review` — the `speckit.implement-review`
  command and every supporting asset, runtime module, configuration key, and integration it
  needs to remain installable, discoverable, and operational. Its behavior MUST NOT change
  except where a dependency must be adjusted because a removed command is being deleted.
- **FR-002**: Before deleting any command-specific file, the implementation MUST produce a
  written inventory of every PowerPack-provided command in the baseline preset, recording
  for each: registration entry, command file, supporting assets, runtime modules,
  configuration keys, documentation references, tests and fixtures, shared dependencies, and
  a final decision of `PRESERVE` or `REMOVE`. The real repository/preset inventory is the
  source of truth; the implementation MUST NOT rely solely on a hand-maintained name list.
- **FR-003**: Every removed command MUST be removed completely: preset `provides` entry,
  command file, command-specific prompts/templates/manifests/metadata, command-specific
  runtime modules, command-specific configuration files and keys, command-specific scripts
  and assets, dedicated tests and fixtures, and operational documentation.
- **FR-004**: After the cleanup, every discovery mechanism PowerPack controls (preset
  registration, manifest, filesystem scan, metadata scan, command generator, or equivalent)
  MUST expose exactly one PowerPack-provided command: `speckit.implement-review`.
- **FR-005**: Every officially supported installation path MUST install only
  `implement-review` as PowerPack command content. The implementation MUST review all
  applicable entrypoints (Linux/WSL, Windows, Python, shell, PowerShell, package-based,
  local-development, and agent-specific). No installer MAY copy, register, generate, or
  reference a removed command.
- **FR-006**: A fresh installation into a clean target MUST result in exactly one
  PowerPack-provided command — `{"speckit.implement-review"}` — with no residual file that
  belongs exclusively to a removed command present in the generated install state.
- **FR-007**: README, installation docs, architecture docs, usage guides, examples,
  portability/compatibility material, and agent instructions MUST reflect the single-command
  baseline and MUST clearly distinguish current capabilities from historical or future ones.
  Documentation pages that exist only to describe a removed command (for example
  `docs/FULL_CYCLE.md`, `docs/TECHNICAL_DEBT.md`) MUST be removed or converted into clearly
  labelled historical records.
- **FR-008**: Historical references MAY remain in changelogs, completed specs, ADRs, and
  merged-PR history where removal would destroy useful context. They MUST NOT imply that a
  removed command is currently available or supported.
- **FR-009**: Tests and fixtures whose only purpose is to validate a removed command MUST be
  deleted. Shared helpers MUST be retained only where still required by `implement-review`,
  core installation, or generic framework behavior.
- **FR-010**: Smoke/homologation tests MUST validate at minimum: (1) successful clean
  installation; (2) discovery of `speckit.implement-review`; (3) exact absence of every
  other PowerPack-provided command; (4) absence of residual removed-command artifacts;
  (5) the minimum operational `implement-review` flow; (6) consistency across supported
  operating-system / install paths.
- **FR-011**: Smoke and contract tests MUST assert set **equality** over the
  PowerPack-provided command namespace, not membership. `registered_powerpack_commands ==
  {"speckit.implement-review"}` and `installed_powerpack_commands ==
  {"speckit.implement-review"}` MUST both hold. A test of the form
  `"speckit.implement-review" in commands` is insufficient on its own.
- **FR-012**: Feature flags, aliases, mappings, constants, paths, environment variables,
  config keys, registry entries, and templates used exclusively by removed commands MUST be
  removed. This includes removed-command entries in `config/default-model-routing.json`,
  `config/default-full-cycle.json`, `config/default-technical-debt.json`,
  `prerequisites.json` defaults, and runtime prerequisite maps — except entries that the
  dependency clarification below preserves.
- **FR-013**: Generic infrastructure MUST remain when required by `implement-review`, the
  installation lifecycle, cross-agent support, shared tests, or the reusable PowerPack core.
  The `powerpack-tools` extension and `bin/powerpack.py` runtime remain in scope only for
  removed-command-specific code paths; their shared surface (doctor, model routing, state
  receipts, review status) MUST be preserved. Command removal MUST NOT become an accidental
  core redesign.
- **FR-014**: Removed commands MUST NOT survive through deprecated aliases, redirects,
  hidden copies, fallback implementations, or compatibility wrappers. No deprecation
  compatibility layer is required or permitted.
- **FR-015**: Where technically applicable, direct invocation of a removed command name MUST
  behave as invocation of an unknown/nonexistent command. The system MUST NOT silently
  redirect the invocation to `implement-review` or any other capability.
- **FR-016**: After removal, the implementation MUST run a repository-wide search for every
  removed command name and classify every occurrence as `ACTIVE_REFERENCE`,
  `HISTORICAL_REFERENCE`, or `FALSE_POSITIVE`. For every removed command,
  `ACTIVE_REFERENCE == 0`.
- **FR-017**: At least one automated test MUST encode the single-command baseline as an
  explicit exact-set contract so that adding or restoring a PowerPack-provided command
  requires an intentional contract change through a new spec or equivalent scope decision.
- **FR-018** *(dependency treatment)*: The implementation MUST keep the `implement-review`
  flow operational end to end. `implement-review` currently depends on a `COMPLETED`
  `implement` state receipt (recorded today by `speckit.implement`) and on `speckit-converge`
  for its Phase 1 convergence loop. The baseline MUST resolve this per
  `[NEEDS CLARIFICATION #1]` below: either preserve `speckit.implement` and `speckit.converge`
  as required dependencies of `implement-review`, or re-base the `implement-review`
  prerequisite gate and convergence step onto upstream Spec Kit `speckit-implement` /
  `speckit-converge` so the PowerPack wraps can be removed without breaking the flow.
- **FR-019**: Installation MUST produce the same PowerPack command inventory on every
  supported platform. A platform-specific installer MAY differ internally but MUST NOT
  produce a different command set.

### Open Clarifications

- **[NEEDS CLARIFICATION #1]**: `implement-review` depends on `speckit.implement` (records
  the `COMPLETED` implement receipt its prereq gate checks) and `speckit.converge` (its
  Phase 1 convergence loop, and re-implementation of appended tasks). Which is the baseline?
  (A) Preserve `speckit.implement` + `speckit.converge` as required dependencies →
  preserved set becomes `{implement-review, implement, converge}`. (B) Re-base the
  `implement-review` gate and convergence step onto upstream Spec Kit `speckit-implement` /
  `speckit-converge` and remove both PowerPack wraps → preserved set stays exactly
  `{implement-review}`. (C) Preserve only the minimal receipt-recording runtime as core
  infrastructure (FR-013), remove the `speckit.implement` / `speckit.converge` command
  templates.
- **[NEEDS CLARIFICATION #2]**: Documentation and homologation scripts under
  `scripts/homologation/` and `docs/` currently cover browserless ChatGPT/GitHub review,
  full-cycle, and technical-debt. Which of these are (a) part of `implement-review`'s own
  supported contract and preserved, versus (b) removed-command support material to delete?
  Specifically: is the browserless ChatGPT Project + GitHub review path an intrinsic part of
  `implement-review` (preserve all its scripts/docs/tests) or an optional gate that may also
  be trimmed?

### Key Entities

- **PowerPack preset (`powerpack-core`)**: the registration surface. Its `provides.templates`
  list is the authoritative inventory of PowerPack-provided commands.
- **Command inventory record**: the per-command `PRESERVE`/`REMOVE` decision table produced
  before deletion (FR-002).
- **Reference classification**: for each removed command name, the set of repository
  occurrences tagged `ACTIVE_REFERENCE` / `HISTORICAL_REFERENCE` / `FALSE_POSITIVE`.
- **Baseline contract test**: the automated exact-set assertion over PowerPack-provided
  commands (FR-017).
- **Install state**: the generated on-disk + registry result of running an installer against
  a clean target, checked independently of installer source.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a clean installation on any supported platform, exactly one
  PowerPack-provided command is exposed for discovery: `speckit.implement-review`
  (count == 1, set equality holds).
- **SC-002**: A repository-wide search for every removed command name returns zero
  `ACTIVE_REFERENCE` occurrences; every remaining occurrence is classified historical or
  false-positive.
- **SC-003**: The minimum supported `implement-review` flow completes on a fixture project
  with a valid completed implementation, with no failure attributable to a removed command
  or a removed runtime helper.
- **SC-004**: Every supported installer produces an identical PowerPack command inventory
  (`{"speckit.implement-review"}`) — zero cross-platform divergence.
- **SC-005**: The full automated test suite passes, and it includes at least one exact-set
  baseline contract test that fails if a second PowerPack-provided command is added.
- **SC-006**: No installed file belonging exclusively to a removed command is present in the
  clean install state (residual-artifact count == 0).
- **SC-007**: Current-state documentation (README + installation + architecture + agent
  instructions) presents `implement-review` as the only current PowerPack capability; a
  reviewer can identify the current supported surface in under 2 minutes from the README
  alone.

## Assumptions

- "001" as the command argument means "work on feature 001" — regenerate this existing spec
  on the standard Spec Kit template and reconcile terminology, not create a new feature.
- The feature directory name stays `specs/001-single-skill-baseline` (no renumbering).
- The unit of removal is the PowerPack-provided preset command. Upstream Spec Kit workflow
  commands / agent skills in the host project's `.claude/skills/` are out of scope and are
  never deleted or renamed by this work.
- `.specify/memory/constitution.md` is still the unpopulated template and imposes no
  concrete constraints on this spec; if it is filled before planning, the plan must re-check.
- The implementation baseline is a recorded commit. The previous draft recorded
  `a825557a0d021e9e9948ad212349bf91d76a619c`; current `main` HEAD is
  `489f5355f7d2b32e50f0c0daa7b6bdb577655338`. The plan MUST record the actual starting SHA
  and explain any inventory delta between `a825557` and the chosen baseline (notably the
  browserless code-review and project-evolution-policy merges #9 and #10).
- The technical-debt lifecycle commands (`debt-create`, `debt-list`, `debt-consult`,
  `debt-start`, `debt-close`), `full-cycle`, and `checklist-converge` are `REMOVE` unless a
  clarification says otherwise — they are not dependencies of `implement-review`.
- This change is intentionally breaking for consumers of removed commands; no migration
  shim is provided.
- "No implementation details / written for non-technical stakeholders" is only partially
  applicable: this is an internal repository-cleanup spec whose subject matter is installers,
  presets, and manifests. File and command names appear because they are the product
  contract, not an implementation choice.

## Installer Contract

Every supported installation path MUST converge on this logical state:

```text
Specify PowerPack
├── core infrastructure (shared runtime, doctor, model routing, state receipts, review status)
└── commands
    └── speckit.implement-review   (+ dependencies preserved per NEEDS CLARIFICATION #1)
```

A platform-specific installer MAY differ internally but MUST NOT produce a different
PowerPack command inventory.

## Repository Verification

After removal, run a repository-wide search for every removed command name. Classify every
occurrence:

```text
ACTIVE_REFERENCE      — advertises or wires a removed command as current  → must be 0
HISTORICAL_REFERENCE  — changelog / completed spec / ADR / merged-PR record → allowed
FALSE_POSITIVE        — unrelated string match                              → allowed
```

For every removed command: `ACTIVE_REFERENCE == 0`.

## Regression Guard

At least one automated test MUST make the single-command baseline an explicit contract:

```text
expected = {"speckit.implement-review"}
assert registered_powerpack_commands == expected
assert installed_powerpack_commands == expected
```

Adding a future PowerPack command MUST therefore require an intentional change to this
contract through a new spec or an equivalent explicit scope decision.

## Risks

- **R-001 — Hidden installer references**: an installer keeps copying legacy content after
  preset cleanup. *Mitigation*: verify the resulting install state, not only installer source.
- **R-002 — Stale documentation**: a removed command stays advertised after code deletion.
  *Mitigation*: global reference scan + current-vs-historical classification (FR-016).
- **R-003 — Shared code accidentally removed**: a helper used by a removed command is also
  needed by `implement-review`. *Mitigation*: inventory shared dependencies before deletion
  (FR-002, FR-013).
- **R-004 — Weak smoke assertion**: checking only that `implement-review` exists lets legacy
  commands linger. *Mitigation*: exact-set equality (FR-011).
- **R-005 — Platform divergence**: Linux/WSL and Windows installers generate different
  inventories. *Mitigation*: enforce the same post-install contract on every platform
  (FR-019, SC-004).
- **R-006 — Breaking `implement-review`**: removing `speckit.implement` / `speckit.converge`
  silently breaks the review flow's prereq gate and convergence loop. *Mitigation*: resolve
  `[NEEDS CLARIFICATION #1]` before implementation; User Story 2 acceptance scenarios.

## Migration Strategy

Intentionally breaking for consumers of removed commands. No deprecation compatibility
layer. Sequence:

1. Record the actual baseline SHA and inventory the preset.
2. Identify shared dependencies and resolve the `implement-review` dependency clarification.
3. Remove non-`implement-review` commands (and preserved dependencies excepted).
4. Clean preset registration and configuration.
5. Update installers.
6. Update documentation.
7. Update automated and smoke tests, including the exact-set baseline contract.
8. Validate clean installations on every supported platform.
9. Run repository-wide residual-reference verification.

Removed capabilities may return later only through explicit new scope decisions compatible
with the architecture current at that time.

## Definition of Done

This spec is complete when every officially supported installation path results in a
PowerPack command inventory of exactly `{"speckit.implement-review"}` (plus any dependency
preserved by `[NEEDS CLARIFICATION #1]`), and implementation, preset registration,
installation, current-state documentation, and smoke-test expectations all describe that
same state.
