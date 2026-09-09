# Feature Specification: Native PowerPack Bundle, Setup and Review Routing

**Feature Branch**: `002-plugin-setup-routing`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Migrate Specify PowerPack to native Spec Kit primitives; define installation, setup, reconfiguration, review routing, companion presets for safe customization of upstream skills, persistent cross-session hook state, and local/cross-agent/GPT Web review configuration."

## Overview

Evolve Specify PowerPack from a bootstrap-oriented companion CLI into a Spec Kit-native
composition whose lifecycle is owned by `specify`.

PowerPack SHALL use three distinct Spec Kit primitives for three distinct responsibilities:

```text
PowerPack Bundle
    |
    +-- PowerPack Extension
    |      -> runtime
    |      -> configuration
    |      -> administrative commands
    |      -> PowerPack-owned functional commands
    |      -> hooks
    |      -> persistent PowerPack state
    |
    +-- PowerPack Preset(s)
           -> compose/wrap/append/override upstream Spec Kit commands only when required
           -> adapt upstream workflow skills without copying their lifecycle into PowerPack
```

The **extension is the runtime core**. Presets are a deliberately narrow customization layer,
not an alternative runtime and not a return to the legacy monolithic `powerpack-core` preset.
The **bundle is the preferred distribution/install unit** when the supported Spec Kit version
provides the native bundle lifecycle, because bundles compose extensions and presets through
their own native managers.

PowerPack MUST NOT install, replace, downgrade, or upgrade the user's Spec Kit CLI as part of
normal operation.

The setup/reconfiguration engine discovers the current Spec Kit integration environment,
validates executable review routes, lets the user explicitly select review policy, and commits
only a complete validated candidate. Runtime execution never silently changes reviewer,
backend, active integration, or evidence source.

This specification also defines a reusable **persistent hook-state contract** for future
PowerPack capabilities. Hook-relevant state MUST survive agent/terminal sessions through
project-local JSON state. Environment variables MAY be projected from that JSON for the
current process, but shell profiles such as `.bashrc`, `.zshrc`, PowerShell profiles, Windows
user/global environment, or equivalent persistent host configuration MUST NOT be modified.

### Dependency on SPEC-001

SPEC-001 establishes `implement-review` as the only functional PowerPack capability at this
baseline. This specification changes installation/lifecycle architecture but does not itself
add another functional workflow capability.

Administrative setup commands, hook infrastructure, presets that customize upstream commands,
and bundle metadata do not by themselves count as new functional PowerPack capabilities.
Future specifications may intentionally expand the functional capability set.

## Architectural Decisions

### AD-001 — Native primitives, not a replacement framework

PowerPack MUST use Spec Kit's supported extension, preset, hook, integration, and bundle
mechanisms instead of maintaining an independent plugin framework.

### AD-002 — Extension owns behavior; presets own composition

The extension owns PowerPack runtime behavior and state. Companion presets are allowed only
where PowerPack must compose an upstream Spec Kit command/skill and the extension API cannot
provide the required command composition semantics.

A preset MUST NOT become the authoritative home for PowerPack runtime, configuration, state,
or business logic.

### AD-003 — Bundle is the preferred install composition

Where supported by the accepted Spec Kit compatibility range, PowerPack SHOULD ship a native
bundle containing the PowerPack extension and required companion preset(s).

Conceptually:

```text
specify bundle install <powerpack-bundle>
```

Development MAY install the primitives independently when that is more useful for debugging.
The technical plan MUST define the exact development, release artifact, direct-install, and
catalog paths for the supported Spec Kit range.

### AD-004 — No permanent copy of upstream skills

When PowerPack needs to customize an upstream skill such as `speckit.checklist`, it SHOULD use
preset composition (`wrap`, `append`, `prepend`, or another native supported strategy as
appropriate) rather than vendoring a permanent fork of the upstream command.

A `replace` strategy that copies the complete upstream command is allowed only when no native
composition strategy can satisfy an accepted requirement, and then it MUST have explicit
compatibility/homologation coverage for upstream drift.

### AD-005 — Persistent hook state is JSON; ENV is transient

Persistent hook/workflow state MUST be represented by project-local JSON owned by PowerPack.
Environment variables are a process-local projection only.

```text
persistent JSON state
        |
        +--> load + validate
                 |
                 +--> project required ENV for current process/hook
```

The inverse relationship is forbidden: ENV MUST NOT be treated as durable workflow authority.

### AD-006 — No shell-profile mutation

PowerPack MUST NOT persist hook ENV through `.bashrc`, `.bash_profile`, `.profile`, `.zshrc`,
PowerShell profiles, Windows registry/user environment variables, or equivalent host-global
configuration.

## Terminology

- **PowerPack Bundle**: native Spec Kit bundle used to distribute/install the set of PowerPack
  primitives required by a release.
- **PowerPack Extension**: primary runtime/configuration component, target id `powerpack`.
- **PowerPack Companion Preset**: minimal native preset used only to compose/customize upstream
  Spec Kit commands where extension commands/hooks are insufficient.
- **Workflow agent**: Spec Kit `default_integration` currently driving the project.
- **Installed integration**: integration recorded by Spec Kit in `installed_integrations`.
- **Active-agent local review**: review executed through the current non-Codex workflow agent.
- **Codex same-session review**: Codex review performed in the active Codex session when Codex
  is the workflow agent.
- **Codex cross-agent review**: Codex used as reviewer while another installed/default agent
  remains responsible for the workflow and fixes.
- **Local backend**: local repository/SPEC evidence and the local `implement-review` contract.
- **GPT Web / ChatGPT Project backend**: existing browserless Codex-authenticated ChatGPT
  Project + GitHub connector evidence path; it is not browser automation.
- **Candidate configuration**: proposed complete configuration that is not active until fully
  validated and atomically committed.
- **Persistent Hook State**: JSON state that records hook-relevant workflow facts across
  sessions.
- **ENV Projection**: temporary environment variables reconstructed from validated persistent
  state for one hook/child process.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Install PowerPack through native Spec Kit composition (Priority: P1)

A user installs PowerPack using the native Spec Kit distribution path. The PowerPack extension
and any companion presets required by that release are installed through their native Spec
Kit managers, preferably as one PowerPack bundle.

**Why this priority**: PowerPack must evolve with Spec Kit rather than wrap and own Spec Kit.

**Independent Test**: Install the release bundle into a clean compatible project and verify
bundle provenance, extension registration, companion-preset registration, command exposure,
and absence of any PowerPack-driven Spec Kit bootstrap/upgrade.

**Acceptance Scenarios**:

1. **Given** a compatible Spec Kit project, **When** the PowerPack bundle is installed,
   **Then** the required extension and preset components are installed through Spec Kit's
   native component managers.
2. **Given** a fresh PowerPack install, **When** setup has not run, **Then** review routing is
   `PENDING`; PowerPack does not guess a reviewer/backend.
3. **Given** a successful install, **When** native Spec Kit list/info commands are used,
   **Then** PowerPack components and provenance are discoverable.
4. **Given** normal installation, **When** the resulting environment is inspected, **Then**
   PowerPack has not installed/replaced/upgraded `specify`.

---

### User Story 2 — Customize upstream skills without forking them (Priority: P1)

A future PowerPack capability needs to add workflow behavior to an upstream Spec Kit skill.
PowerPack installs/uses a companion preset that composes the upstream command while the
PowerPack extension provides the reusable runtime and state implementation.

**Why this priority**: Future skills such as checklist convergence need upstream workflow
integration while still surviving Spec Kit evolution.

**Independent Test**: Compose an upstream command through a PowerPack companion preset,
upgrade/re-render the integration, and verify that upstream behavior remains present while the
PowerPack augmentation remains isolated and removable.

**Acceptance Scenarios**:

1. **Given** an upstream command can be augmented by a native preset composition strategy,
   **When** PowerPack customization is installed, **Then** PowerPack MUST use composition
   rather than copy the complete upstream command.
2. **Given** the preset invokes PowerPack logic, **When** its implementation is inspected,
   **Then** substantive behavior resides in extension/runtime code or PowerPack-owned command
   logic rather than duplicated inside the preset prompt.
3. **Given** the preset is removed/disabled, **When** the integration is rescaffolded,
   **Then** upstream Spec Kit command behavior remains available without PowerPack-specific
   augmentation.
4. **Given** native composition is insufficient and `replace` is proposed, **When** the change
   is planned, **Then** explicit upstream-drift tests and a documented reason are required.

---

### User Story 3 — Setup detects the real Spec Kit/AI environment (Priority: P1)

A user runs PowerPack setup. PowerPack reads authoritative Spec Kit integration state,
validates actual local CLI/auth capabilities, and exposes only executable review strategies or
explicit actions required to make another strategy executable.

**Acceptance Scenarios**:

1. `default_integration = codex` exposes Codex same-session local review.
2. Non-Codex default with no ready Codex exposes active-agent local review only.
3. Non-Codex default plus installed/ready/authenticated Codex exposes Codex cross-agent review.
4. Codex recorded but executable/auth unavailable does not count as a ready Codex reviewer.
5. Cross-agent review MUST NOT silently change `default_integration`.

---

### User Story 4 — Configure local, cross-agent, and GPT Web review plans (Priority: P1)

The user chooses an explicit review topology and evidence/backend strategy. Local active-agent,
Codex same-session, Codex cross-agent, and Codex-backed GPT Web gates are composed only when
the detected environment supports them.

**Acceptance Scenarios**:

1. Active non-Codex integration can run the existing local review flow.
2. Active Codex can run same-session local review without spawning another Codex merely to
   simulate independence.
3. Non-Codex + ready secondary Codex can run cross-agent review without changing workflow
   ownership.
4. GPT Web may be added only to a Codex-backed route.
5. Invalid combinations fail during candidate validation and are never silently rewritten.

---

### User Story 5 — GPT Web requires a compatible bound Project (Priority: P1)

When GPT Web is selected, PowerPack requires explicit binding to a compatible ChatGPT Project
and validates GitHub connector/repository evidence before configuration becomes active.

**Acceptance Scenarios**:

1. No valid ChatGPT Project binding means GPT Web cannot become `READY`.
2. Project selection cancellation causes zero setup/reconfiguration modifications.
3. Project/context/GitHub/repository validation failure causes zero candidate commit.
4. A previous valid configuration survives failed reconfiguration unchanged.
5. Credentials/tokens/cookies are never persisted in PowerPack project configuration.

---

### User Story 6 — Setup is transactional and re-runnable (Priority: P1)

Setup can be executed at installation time or any later time. It always builds a candidate,
validates it completely, and atomically replaces the prior configuration only after success.

**Acceptance Scenarios**:

1. Running setup against `READY` enters reconfiguration semantics.
2. Selective changes preserve unspecified values only when the complete resulting candidate
   is still valid.
3. Abort/reject/failure preserves the prior configuration exactly.
4. Runtime environment drift blocks with `BLOCKED_CONFIGURATION`; no silent fallback occurs.
5. Reset is a distinct explicit operation, not an implicit consequence of reconfiguration.

---

### User Story 7 — Setup works from AI skill and shell (Priority: P2)

A user can run setup through the active AI integration or from a shell. Both adapters invoke
one setup engine.

**Acceptance Scenarios**:

1. `speckit.powerpack.setup` supports interactive invocation.
2. Agent command arguments are accepted where the integration provides an argument channel.
3. A portable extension-owned Python entrypoint supports shell/non-interactive operation.
4. Equivalent arguments through agent and shell produce equivalent validated configuration.

---

### User Story 8 — Configure bounded automatic review rounds (Priority: P1)

Setup stores a maximum automatic round budget. Review stops early when all required gates
approve the same immutable snapshot and never treats budget exhaustion as approval.

**Acceptance Scenarios**:

1. Default `max_rounds` is 5 unless a later accepted specification changes it.
2. Approval before the budget is exhausted stops further rounds.
3. Findings are carried forward and accounted for in subsequent rounds.
4. Any fix that changes the snapshot invalidates prior approval for that snapshot.
5. Unresolved state at the limit returns `BLOCKED_BUDGET` or a more specific blocking state.

---

### User Story 9 — Persist hook state across sessions without shell profiles (Priority: P1)

A PowerPack hook derives workflow facts that later hooks or later sessions need. PowerPack
persists those facts in a project-local JSON state file. The current hook/process may project
selected values into environment variables, but no persistent shell/user environment is
modified.

This contract is intentionally generic so future capabilities such as checklist convergence
can persist facts such as pending gaps, ambiguities, conflicts, or clarification requirements
without inventing their own persistence mechanism.

**Independent Test**: Produce hook state in one agent session, terminate that session, start a
new session (including a different supported agent), load the same checkout, execute a
PowerPack hook, and verify that validated JSON state is recovered and the same effective hook
facts are reconstructed.

**Acceptance Scenarios**:

1. **Given** a workflow state is produced after an upstream command, **When** PowerPack needs
   the state later, **Then** it is loaded from JSON rather than a shell profile.
2. **Given** a new terminal/AI session, **When** the relevant PowerPack hook runs, **Then** it
   can recover the state from the same project checkout.
3. **Given** a different supported AI integration in a later session, **When** it loads the
   project, **Then** hook state semantics remain independent of the agent that produced them.
4. **Given** persisted state no longer matches the referenced artifacts, **When** a hook loads
   it, **Then** it is marked/recomputed as stale before consequential action.
5. **Given** ENV values are needed by a child hook/runtime process, **When** the hook executes,
   **Then** they are reconstructed from validated JSON only for that process/session.

## Persistent Hook-State Model

### Source of truth

The source of truth is a PowerPack-owned JSON artifact under mutable project state, not inside
extension-managed source files.

The exact final path is resolved by the technical plan. A conceptual layout is:

```text
.specify/powerpack/state/
    hooks/
        <workflow-or-feature-key>.json
```

A future capability MAY use a more specific file such as:

```text
.specify/powerpack/state/checklist-state.json
```

provided it conforms to the common state contract.

### Minimum envelope

Persistent hook state SHOULD contain at minimum:

```json
{
  "schema_version": 1,
  "state_type": "<type>",
  "spec": "<active-spec-id>",
  "source_artifacts": [
    {
      "path": "<relative-path>",
      "digest": "sha256:<digest>"
    }
  ],
  "status": "<semantic-status>",
  "facts": {},
  "updated_at": "<timestamp>"
}
```

Capability-specific specifications define the allowed `status` and `facts` values.

### Hook execution flow

The generic lifecycle is:

```text
upstream command completes
        |
        v
PowerPack post hook executes
        |
        +--> discover relevant output/artifacts
        +--> load prior JSON state when applicable
        +--> validate artifact identity/digests
        +--> analyze/refresh semantic state
        +--> atomically persist JSON state
        +--> project selected facts to current process ENV when useful
        +--> decide/report next action
```

For later sessions:

```text
new AI/terminal session
        |
        v
PowerPack hook/command
        |
        +--> load JSON
        +--> validate freshness
        +--> recompute if stale
        +--> project runtime ENV
        +--> continue
```

### ENV projection

ENV names are implementation/API details defined by the capability that consumes them. They
MUST be derived from validated persistent state and MUST NOT be the only copy of a workflow
fact.

Conceptually:

```text
ENV = projection(validated_persistent_state)
```

The following is explicitly forbidden:

```text
persistent_state = assumption_from_current_ENV
```

except for unrelated external environment configuration that is independently authoritative
(e.g. an external tool's own documented authentication/config contract).

### First post-hook rule

A post hook that is responsible for discovering/persisting a workflow state MUST NOT require a
pre-existing projected ENV in order to run. That would create a circular dependency.

Therefore the initial state-producing hook executes unconditionally (subject to the normal
hook enabled/disabled lifecycle), loads/analyzes its artifacts, writes/updates JSON, and only
then projects runtime ENV or routes subsequent internal behavior.

This rule is especially important for a future `after_checklist` integration: the hook cannot
be conditioned on `POWERPACK_CHECKLIST_*` ENV before the first checklist state has been
produced.

## Edge Cases

- Missing/unreadable `.specify/integration.json`: fail closed; do not infer the active agent
  from `.claude`, `.agents`, or similar directories.
- Codex registered but executable/auth missing: Codex-backed routes are unavailable.
- User asks PowerPack to add Codex integration: show/offer the native Spec Kit action only
  after explicit consent; never mutate integration state silently.
- Default integration changes: rediscover and revalidate; do not rewrite review policy
  automatically.
- GPT Web Project ambiguous/inaccessible or GitHub evidence unavailable: no GPT Web commit.
- Setup interrupted before commit: active configuration unchanged.
- Bundle installation failure: PowerPack MUST NOT claim setup readiness. Because native bundle
  rollback is best-effort, diagnostics MUST detect partial primitive state and provide an
  actionable cleanup/retry path rather than assuming perfect rollback.
- Companion preset removed while extension remains: PowerPack-owned commands continue where
  independent; upstream augmentation is reported unavailable rather than silently recreated
  outside the native preset lifecycle.
- Preset drift after a Spec Kit upgrade: compatibility/homologation catches unsupported
  command-composition behavior before expanding the declared supported version range.
- Hook JSON missing: treat state as not evaluated and rebuild when source artifacts allow it.
- Hook JSON malformed/schema-incompatible: fail closed for consequential actions and rebuild
  only when deterministic.
- Hook JSON digest differs from current source artifact: mark `STALE`, re-evaluate before use.
- Multiple sessions write the same state concurrently: persistence MUST use atomic replacement
  and SHOULD use conflict detection/serialization defined by the technical plan.
- Repository is copied to another machine: project-local hook state remains usable only after
  artifact digests and environment-dependent facts are revalidated.

## Requirements *(mandatory)*

### Native distribution and ownership

- **FR-001**: PowerPack MUST use native Spec Kit primitives for supported installation and
  lifecycle management.
- **FR-002**: The PowerPack extension SHALL be the authoritative runtime/config/state core.
- **FR-003**: PowerPack MAY ship one or more companion presets when upstream command
  composition/customization is required.
- **FR-004**: Where native Spec Kit bundles are supported by the accepted compatibility range,
  PowerPack SHOULD provide a bundle as the preferred release/install unit containing the
  required extension and companion presets.
- **FR-005**: PowerPack MUST NOT install/replace/downgrade/upgrade the Spec Kit CLI in normal
  operation.
- **FR-006**: Extension/preset/bundle manifests MUST declare explicit compatible Spec Kit
  version constraints according to their native schemas.
- **FR-007**: A fresh install MUST leave review setup `PENDING`; no review route is guessed.
- **FR-008**: Because stable extension `on_install` execution is not assumed, installation
  MUST NOT depend on an automatic interactive post-install wizard. Users are directed to
  `speckit.powerpack.setup` when configuration is required.

### Preset customization contract

- **FR-009**: Companion presets MUST be narrowly scoped to upstream Spec Kit command
  composition/customization and MUST NOT become the primary PowerPack runtime.
- **FR-010**: PowerPack SHOULD prefer native non-destructive composition (`wrap`, `append`,
  `prepend`, or equivalent supported semantics) over copying/replacing an upstream command.
- **FR-011**: A full `replace` of an upstream command MUST require documented necessity and
  explicit compatibility tests against every supported Spec Kit version boundary.
- **FR-012**: Presets MUST delegate reusable logic/state handling to the PowerPack extension
  runtime or PowerPack-owned commands rather than duplicate complex logic in prompt text.
- **FR-013**: Removing/disabling a PowerPack companion preset MUST leave the upstream core
  command available through normal Spec Kit behavior.
- **FR-014**: The technical plan MUST define how companion presets are versioned relative to
  the extension and bundle and how compatibility drift is homologated.

### Environment and capability discovery

- **FR-015**: `.specify/integration.json` or an equivalent stable machine-readable Spec Kit
  interface is authoritative for `default_integration` and `installed_integrations`.
- **FR-016**: Agent-specific directories MUST NOT be the primary source of integration truth.
- **FR-017**: Runtime executable/auth readiness MUST be validated independently from Spec Kit
  registration.
- **FR-018**: Setup MUST build a capability model before offering/accepting strategies.
- **FR-019**: User parameters express intent but do not bypass capability validation.
- **FR-020**: Optional integration changes require explicit user consent.
- **FR-021**: Cross-agent review MUST NOT silently change `default_integration`.

### Review routing

- **FR-022**: Executor/topology and evidence backend MUST be modeled as separate dimensions.
- **FR-023**: Non-Codex workflow agents MUST support active-agent local review where the
  integration can execute the local contract.
- **FR-024**: Codex default MUST support same-session local review.
- **FR-025**: Non-Codex default plus ready secondary Codex MUST support Codex cross-agent local
  review.
- **FR-026**: Ordered review gates MAY be configured; cheaper/local gates SHOULD precede GPT
  Web when both are enabled.
- **FR-027**: All required final gates MUST approve the same immutable final snapshot.
- **FR-028**: Runtime capability loss MUST return `BLOCKED_CONFIGURATION`; no silent reviewer,
  topology, backend, or gate-order fallback is allowed.

### GPT Web / ChatGPT Project

- **FR-029**: GPT Web MUST reuse the browserless ChatGPT Project + GitHub evidence provider;
  browser automation/cookie/profile fallbacks are prohibited.
- **FR-030**: GPT Web MUST be Codex-backed unless a future accepted specification adds another
  validated provider.
- **FR-031**: `backend == chatgpt-project` implies a successfully validated compatible Project
  binding.
- **FR-032**: Binding validation MUST include Project access/identity/context plus GitHub
  connector, repository access, and required evidence readiness.
- **FR-033**: Cancelled/failed GPT Web binding MUST commit no candidate configuration.
- **FR-034**: Secrets/tokens/cookies/OAuth credentials MUST NOT be persisted in PowerPack
  project configuration.

### Transactional setup and reconfiguration

- **FR-035**: Setup/reconfiguration MUST build a complete candidate in memory/temporary state,
  validate it, obtain required confirmation, then atomically commit it.
- **FR-036**: Candidate fields MUST NOT be progressively persisted before final commit.
- **FR-037**: Abort/cancel/rejection/validation failure MUST preserve the previous active
  configuration exactly.
- **FR-038**: First-time failed/aborted setup leaves installation-created `PENDING` state.
- **FR-039**: Configuration commit MUST use atomic replacement or an equivalent partial-write
  safe mechanism.
- **FR-040**: Reconfiguration MUST be available at any time.
- **FR-041**: Reset/removal of configuration MUST be a distinct explicit action.
- **FR-042**: Environment-owned integration facts MUST be rediscovered, not duplicated as
  competing PowerPack authority.

### Setup interfaces

- **FR-043**: `speckit.powerpack.setup` MUST support interactive setup and argument-driven
  intent where the active integration supports arguments.
- **FR-044**: A portable shell entrypoint MUST exist without requiring the legacy global
  `specify-powerpack` CLI; the initial target is an extension-owned Python script.
- **FR-045**: Agent and shell adapters MUST use one setup engine.
- **FR-046**: Full parameters MUST enable non-interactive setup; TTY execution MAY prompt for
  missing required choices.
- **FR-047**: Interactive reconfiguration MUST show current effective policy and newly
  discovered capabilities before commit.

### Automatic review rounds

- **FR-048**: Setup MUST configure a maximum automatic review-round budget; default is 5.
- **FR-049**: `max_rounds` MUST be a positive bounded integer; the plan defines the upper
  bound.
- **FR-050**: Review stops early when all mandatory gates approve the current common snapshot.
- **FR-051**: Later rounds MUST explicitly account for earlier findings.
- **FR-052**: Snapshot-changing fixes invalidate prior approvals for the old snapshot.
- **FR-053**: Budget exhaustion with unresolved state MUST NOT produce approval.
- **FR-054**: Existing local `implement-review` convergence, quality-gate, repair, and fresh
  review semantics remain unless explicitly changed by a later specification.

### Persistent hook-state contract

- **FR-055**: Durable hook/workflow facts MUST be persisted in PowerPack-owned project-local
  JSON state, not persistent environment variables.
- **FR-056**: PowerPack MUST NOT modify `.bashrc`, `.bash_profile`, `.profile`, `.zshrc`,
  PowerShell profiles, Windows user/global environment, or equivalent host profiles to persist
  hook state.
- **FR-057**: Environment variables required by hooks MAY be projected only from validated
  persistent JSON for the current process/child process/session.
- **FR-058**: A state-producing post hook MUST NOT require those projected ENV values in order
  to execute for the first time.
- **FR-059**: The state-producing post hook MUST load relevant prior JSON when present,
  validate source-artifact identity/freshness, derive current semantic state, and atomically
  persist the refreshed JSON before exposing consequential state to later execution.
- **FR-060**: Persistent hook state MUST carry schema version and sufficient artifact identity
  (including digest or equivalent) to detect stale state.
- **FR-061**: Stale hook state MUST be recomputed/revalidated before it can authorize/block a
  consequential workflow transition.
- **FR-062**: The same persisted hook state MUST be consumable across separate AI/terminal
  sessions and across different supported active integrations working on the same checkout.
- **FR-063**: Capability-specific specifications MUST define their own semantic statuses/facts
  while reusing this common persistence/projection contract.
- **FR-064**: Concurrent writes to one hook-state record MUST not expose partial JSON; the
  technical plan MUST define atomic write and conflict/serialization behavior.

### Drift, migration, update and removal

- **FR-065**: Before `implement-review`, PowerPack MUST rediscover enough runtime capability
  state to prove the configured route remains executable.
- **FR-066**: Changing Spec Kit default integration MUST not automatically rewrite PowerPack
  policy; it triggers later validation/reconfiguration as needed.
- **FR-067**: Legacy migration MUST distinguish managed code, mutable config, persistent hook
  state, Project binding metadata, and generated review evidence.
- **FR-068**: Extension/preset/bundle update migrations MUST preserve the previous recoverable
  config/state if migration cannot complete safely.
- **FR-069**: Removal/update MUST NOT silently delete historical review evidence or other
  mutable user/workflow state unless explicitly requested.
- **FR-070**: PowerPack MUST homologate the complete bundle composition against supported Spec
  Kit versions, including extension registration, preset composition, integration switching,
  hook behavior, and state persistence.

## Key Entities

- **PowerPack Bundle**: versioned install composition referencing the release's extension and
  companion preset set.
- **PowerPack Extension**: runtime/configuration/hooks/commands/state core.
- **PowerPack Companion Preset**: narrow upstream-command composition adapter.
- **PowerPack Setup State**: `PENDING`/`READY`, schema version, and setup metadata.
- **Environment Capability Snapshot**: transient discovery of Spec Kit integrations, local
  executables, authentication and supported routes.
- **Review Policy**: ordered gates, executor/topology, backend, `max_rounds`, early-stop rules.
- **ChatGPT Project Binding**: non-secret stable Project identity/validation metadata.
- **Candidate Configuration**: temporary complete proposed setup state.
- **Review Round**: one immutable-snapshot review attempt linked to prior findings.
- **Persistent Hook State**: cross-session JSON facts plus artifact freshness metadata.
- **ENV Projection**: ephemeral current-process representation derived from Persistent Hook
  State.

## Success Criteria

- **SC-001**: Clean supported installation can install/discover PowerPack through native Spec
  Kit component/bundle lifecycle without PowerPack bootstrapping Spec Kit.
- **SC-002**: Removing PowerPack companion presets leaves upstream Spec Kit commands intact.
- **SC-003**: No supported customization requires a permanent copied upstream skill unless an
  explicitly documented/validated `replace` exception exists.
- **SC-004**: Capability fixtures expose exactly valid review routes for Codex-default,
  non-Codex-default, and non-Codex+secondary-Codex environments.
- **SC-005**: Setup cancellation/failure injection preserves pre-run active configuration in
  100% of tested stages.
- **SC-006**: GPT Web never reaches `READY` without validated compatible Project + GitHub
  evidence.
- **SC-007**: Equivalent agent/shell setup inputs produce equivalent configuration.
- **SC-008**: Runtime capability removal yields zero silent fallback events.
- **SC-009**: Review never exceeds `max_rounds`, stops early on common approval, and never
  reports approval after unresolved budget exhaustion.
- **SC-010**: A hook-state fixture persisted in one session can be recovered in another
  session and produce equivalent semantic state after freshness validation.
- **SC-011**: Homologation detects zero writes to user shell profiles/host-global ENV while
  exercising persistent hook state on Linux/WSL and Windows.
- **SC-012**: Stale/malformed hook-state fixtures never authorize a consequential transition
  without validation/recomputation.

## Assumptions

- SPEC-001 has reduced the current functional PowerPack capability set to `implement-review`.
- The supported Spec Kit range provides native extensions, presets, hooks, machine-readable
  integration state, and—where selected as the preferred install path—bundles.
- Bundle installation composes primitive managers; PowerPack does not assume bundle rollback
  is perfectly atomic and therefore performs post-install diagnostics before setup readiness.
- Codex and other reviewer CLIs own their own installation/authentication; PowerPack detects
  readiness but does not persist credentials.
- The browserless ChatGPT Project/GitHub provider is migrated into the native PowerPack
  runtime rather than replaced.
- Python is available in supported environments for the initial portable shell entrypoint.
- Persistent hook state is project/workflow state and is stored outside extension-managed
  immutable source assets.

## Non-Goals

- Adding a new functional PowerPack workflow capability beyond `implement-review` in this
  specification.
- Forking Spec Kit to add lifecycle behavior.
- Making presets the main PowerPack runtime.
- Maintaining a permanent fork of upstream Spec Kit skills when native composition suffices.
- Automatically changing the user's default Spec Kit integration.
- Automatically installing another integration without explicit consent.
- Browser automation for GPT Web.
- Persisting reviewer credentials in project files.
- Persisting hook/workflow state through shell profiles or global environment configuration.
- Treating ENV as cross-session workflow authority.

## Core Invariants

```text
PowerPack lifecycle owner == Specify
```

```text
PowerPack distribution
  == native bundle when supported/preferred
  == extension + required companion presets
```

```text
PowerPack runtime authority == extension
```

```text
preset responsibility == upstream command composition only
```

```text
functional PowerPack capabilities == {implement-review}
```

```text
PERSISTENT_HOOK_STATE == project_local_json
ENV == projection(validated(PERSISTENT_HOOK_STATE))
```

```text
persistent_hook_state
  != bashrc
  != shell_profile
  != host_global_environment
```

```text
STATE_PRODUCING_POST_HOOK
  => executes without requiring preexisting projected ENV
  => validates artifacts
  => atomically persists JSON
  => may then project ENV
```

```text
new_session
  => load JSON
  => validate freshness
  => recompute if stale
  => project runtime ENV
```

```text
GPT_WEB_ENABLED
  => CODEX_BACKED_ROUTE
  => COMPATIBLE_CHATGPT_PROJECT_BOUND
  => GITHUB_EVIDENCE_READY
```

```text
SETUP_ABORTED or SETUP_FAILED
  => persisted_configuration_after == persisted_configuration_before
```

```text
CONFIGURATION_COMMIT
  => COMPLETE_CANDIDATE_VALIDATED
```

```text
RUNTIME_ROUTE_INVALID
  => BLOCKED_CONFIGURATION
  != SILENT_FALLBACK
```

```text
final_approval
  => all_required_gates_approve_same_immutable_snapshot
```
