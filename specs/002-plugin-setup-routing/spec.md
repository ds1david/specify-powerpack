# Feature Specification: Native PowerPack Bundle, Setup and Review Routing

**Feature Branch**: `002-plugin-setup-routing`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Migrate Specify PowerPack to native Spec Kit primitives; define installation, setup, reconfiguration, review routing, companion presets for safe customization of upstream skills, persistent cross-session hook state, modular capability setup, component coherence, diagnostics, and local/cross-agent/GPT Web review configuration."

## Overview

Evolve Specify PowerPack from a bootstrap-oriented companion CLI into a Spec Kit-native composition whose lifecycle is owned by `specify`.

PowerPack SHALL use native Spec Kit primitives with explicit responsibility boundaries:

```text
PowerPack Bundle
    |
    +-- PowerPack Extension
    |      -> runtime
    |      -> capability registry
    |      -> setup/configuration engine
    |      -> administrative commands
    |      -> PowerPack-owned functional commands
    |      -> hooks/events adapters
    |      -> persistent PowerPack state
    |      -> diagnostics
    |
    +-- PowerPack Preset(s)
           -> compose/wrap/append/prepend upstream Spec Kit commands when required
           -> adapt upstream workflow skills without permanently copying them
```

The **extension is the runtime authority**. Presets are a narrow composition layer, not a second runtime and not a return to the legacy monolithic `powerpack-core` preset. The **bundle is the preferred release/install composition** where the supported Spec Kit range provides the native bundle lifecycle.

PowerPack MUST NOT install, replace, downgrade, or upgrade the user's Spec Kit CLI during normal operation.

The setup engine MUST be modular by capability. It aggregates capability descriptors, discovers the environment once, builds a complete candidate configuration, validates global and capability-local invariants, and commits only a complete valid candidate. Adding a future capability MUST NOT require turning `setup.py` into a hard-coded chain of feature-specific conditionals.

This specification also defines a reusable persistent hook-state contract. Durable workflow facts live in project-local JSON. Environment variables are optional child-process projections only; they are not cross-hook or cross-session authority and MUST NOT be persisted through shell profiles or host-global environment configuration.

### Dependency on SPEC-001

SPEC-001 establishes `implement-review` as the only functional PowerPack capability at this baseline. SPEC-002 changes installation/runtime architecture and adds administrative infrastructure but does not itself add a new functional workflow capability.

Administrative setup, doctor/diagnostics, capability registry, state handling, presets, hooks/events adapters, bundle metadata, and machine-readable status surfaces do not count as additional functional capabilities.

## Architectural Decisions

### AD-001 — Native primitives, not a replacement framework

PowerPack MUST use supported Spec Kit extensions, presets, hooks/events, integrations, workflows/bundles where appropriate, rather than maintaining an independent plugin framework.

### AD-002 — Extension owns runtime; presets own upstream composition

Reusable logic, state, validation, configuration, routing, and diagnostics belong to the extension runtime. Presets MAY compose upstream Spec Kit commands when the extension API alone cannot supply the required composition behavior.

Preset prompt text MUST remain thin and MUST delegate substantive logic to PowerPack-owned commands/runtime.

### AD-003 — Bundle is the preferred release composition

Where supported by the accepted Spec Kit compatibility range, PowerPack SHOULD ship a native bundle containing the extension and all required companion presets.

Development MAY install components independently for debugging. Release/homologation MUST validate the exact component set delivered to users.

### AD-004 — No permanent fork of upstream skills

PowerPack SHOULD use `wrap`, `append`, `prepend`, or another native composition mechanism to augment upstream skills. A full `replace` is an exception requiring documented necessity and explicit upstream-drift tests.

### AD-005 — Capability registry is the setup/runtime expansion point

Each PowerPack capability MUST be representable by a capability descriptor that can declare, as applicable:

```text
id
version
kind: functional | administrative
configuration schema/defaults
runtime dependencies
readiness evaluator
hook/event registrations
persistent-state schema(s)
migration provider
health checks
machine-readable status fields
```

The setup engine, doctor, status output, migration engine, and future UI adapters SHOULD consume this common registry rather than maintain independent capability lists.

### AD-006 — Installation health and capability readiness are separate

PowerPack MUST distinguish installation/component health from individual capability readiness.

```text
installation_health:
  HEALTHY | DEGRADED | BROKEN

capability_state:
  UNCONFIGURED | READY | BLOCKED | DISABLED
```

A healthy installation MAY legitimately contain a disabled or unconfigured optional capability. A blocked optional capability MUST NOT make unrelated ready capabilities unusable unless there is an explicit dependency.

### AD-007 — Component coherence is verified, not assumed

Bundle, extension, presets, and any future distribution components MUST expose enough identity/version metadata for PowerPack to verify that the installed component set is compatible.

Because bundle/component installation can be idempotent by component id rather than guaranteed version replacement, merely finding a component installed is insufficient proof of coherence.

A component-set check MUST detect extension/preset/bundle skew before declaring the relevant capability ready.

### AD-008 — Persistent state is JSON; ENV is child-process projection only

Durable hook/workflow facts MUST be stored in PowerPack-owned project-local JSON.

```text
JSON persistent state
    -> load
    -> schema/freshness/concurrency validation
    -> optional ENV projection for a child process controlled by PowerPack
```

An ENV value exported by one hook MUST NOT be assumed to survive after that hook exits or propagate back to the parent agent process. Separate hooks/commands MUST reload authoritative JSON or invoke a PowerPack state resolver.

### AD-009 — No shell-profile or host-global ENV mutation

PowerPack MUST NOT persist workflow state by modifying `.bashrc`, `.bash_profile`, `.profile`, `.zshrc`, PowerShell profiles, Windows user/global environment, registry environment entries, or equivalent host-global configuration.

### AD-010 — Atomic write plus optimistic concurrency

Atomic replacement prevents partial JSON but does not by itself prevent lost updates. Persistent state MUST therefore carry a revision/generation token and writes MUST detect whether the record changed since it was read.

Conceptually:

```text
read revision N
compute candidate
verify current revision still N
commit revision N+1
or reload/reconcile on conflict
```

The technical plan MAY use a portable lock in addition to revision checking.

### AD-011 — Config, state, and evidence are different data classes

PowerPack MUST keep different lifecycle semantics for:

```text
CONFIG     -> durable user intent/policy
STATE      -> mutable workflow/runtime continuity
EVIDENCE   -> historical/audit review outputs
```

The technical plan MUST define concrete paths and git-ignore behavior. Mutable runtime state SHOULD be gitignored by default. Cross-machine synchronization of mutable state is not implicit and requires a future explicit capability if desired.

### AD-012 — Native runtime events are an optional accelerator, not a portability dependency

When the active integration supports Spec Kit agent-native events such as `session_start`, PowerPack MAY use them to bootstrap/validate state, component coherence, or health. Capabilities MUST still work through the portable command/hook contract when such native events are unavailable.

### AD-013 — UI/canvas integrations consume machine-readable state; they do not own workflow semantics

PowerPack MUST expose enough machine-readable capability/status information that a future Copilot Canvas or other UI adapter can discover and render PowerPack state.

The PowerPack runtime MUST remain agent-agnostic. A Copilot-specific canvas is an optional adapter layer and MUST NOT become required for PowerPack operation.

## Terminology

- **PowerPack Bundle**: native Spec Kit release composition for the extension plus required companion presets/components.
- **PowerPack Extension**: authoritative runtime/configuration/hooks/state component, target id `powerpack`.
- **PowerPack Companion Preset**: thin native preset that composes an upstream Spec Kit command.
- **Capability Descriptor**: machine-readable/internal contract describing one PowerPack functional or administrative capability.
- **Installation Health**: health of the installed PowerPack component set independent from individual capability configuration.
- **Capability State**: readiness state of one capability.
- **Component Set**: bundle/extension/preset versions and compatibility identity expected to operate together.
- **Persistent Hook State**: project-local JSON workflow facts that survive sessions.
- **ENV Projection**: temporary child-process environment derived from validated JSON.
- **Workflow agent**: Spec Kit `default_integration` driving the project.
- **Installed integration**: integration recorded in Spec Kit `installed_integrations`.
- **Codex same-session review**: review performed in the active Codex workflow/session.
- **Codex cross-agent review**: Codex used as secondary reviewer while another agent remains workflow/fix owner.
- **GPT Web / ChatGPT Project backend**: browserless Codex-authenticated ChatGPT Project + GitHub connector evidence route.
- **Candidate configuration**: complete proposed setup state that is inactive until validated and atomically committed.

## User Scenarios & Testing

### User Story 1 — Install PowerPack through native Spec Kit composition (Priority: P1)

A user installs the PowerPack bundle in a compatible Spec Kit project. Spec Kit manages the extension and presets; PowerPack does not bootstrap or upgrade Spec Kit.

**Acceptance Scenarios**:

1. Required components are installed through their native Spec Kit managers.
2. Fresh installation has healthy component metadata but capability setup may remain `UNCONFIGURED`/`PENDING`.
3. Native list/info surfaces can discover installed components and provenance.
4. PowerPack does not install/replace/upgrade `specify`.
5. Post-install diagnostics detect partial or skewed component sets before setup reports ready.

### User Story 2 — Customize upstream skills without forking them (Priority: P1)

A PowerPack capability augments an upstream Spec Kit command through a narrow companion preset while substantive logic stays in the extension runtime.

**Acceptance Scenarios**:

1. Native composition is preferred over copying the complete upstream command.
2. Removing the preset leaves the upstream core command functional.
3. `replace` requires documented necessity and upstream compatibility tests.
4. Multiple composing presets from different sources are included in homologation for ordering/priority/conflict behavior.

### User Story 3 — Setup aggregates capability modules (Priority: P1)

The setup engine discovers registered PowerPack capabilities and asks each applicable descriptor to validate/configure its own section, while sharing one environment discovery and one transactional candidate.

**Acceptance Scenarios**:

1. Adding a new capability descriptor does not require a duplicate setup engine.
2. One capability may be `READY` while another is `UNCONFIGURED` or `DISABLED`.
3. A blocked optional capability does not silently disable unrelated capabilities.
4. Capability-local validation and global cross-capability validation both run before commit.
5. Agent and shell setup adapters invoke the same registry-driven engine.

### User Story 4 — Verify component coherence (Priority: P1)

PowerPack verifies that installed bundle/extension/preset versions form a supported component set before capability execution.

**Acceptance Scenarios**:

1. Matching supported components yield `HEALTHY` installation health.
2. Missing required preset, extension/preset skew, or unsupported Spec Kit range yields `DEGRADED` or `BROKEN` with actionable diagnostics.
3. PowerPack never silently rewrites/reinstalls components outside native lifecycle commands.
4. Re-running native bundle update followed by doctor can restore health.

### User Story 5 — Setup detects the real Spec Kit/AI environment (Priority: P1)

Setup reads authoritative Spec Kit integration state and validates actual executable/auth capabilities before offering review routes.

**Acceptance Scenarios**:

1. Codex default exposes same-session review.
2. Non-Codex default with no ready Codex exposes active-agent local review only.
3. Non-Codex default plus ready authenticated Codex exposes cross-agent review.
4. Registration without executable/auth readiness does not count as runnable capability.
5. Cross-agent review never silently changes `default_integration`.

### User Story 6 — Configure review topology and GPT Web safely (Priority: P1)

The user selects explicit review gates/topology. GPT Web is available only when its Codex-backed ChatGPT Project/GitHub evidence prerequisites validate.

**Acceptance Scenarios**:

1. Executor/topology and evidence backend are separate dimensions.
2. Invalid combinations fail before persistence.
3. GPT Web requires a uniquely validated compatible Project and repository evidence path.
4. Cancellation/failure preserves the previous valid configuration exactly.
5. Credentials/tokens/cookies are never stored in project configuration.

### User Story 7 — Run bounded sequential review rounds (Priority: P1)

`implement-review` executes configured gates against immutable snapshots and stops early on common approval.

**Acceptance Scenarios**:

1. Default `max_rounds` is 5 unless superseded later.
2. Findings are explicitly accounted for in later rounds.
3. Snapshot-changing fixes invalidate previous approvals.
4. Exhausted budget with unresolved findings returns blocking state, never approval.

### User Story 8 — Persist hook state safely across sessions (Priority: P1)

A state-producing hook writes validated JSON that can be recovered by later commands/hooks/sessions, including another supported agent using the same checkout.

**Acceptance Scenarios**:

1. Later consumers reload JSON; they do not depend on ENV exported by a previous hook.
2. JSON includes schema, revision and artifact identity/freshness metadata.
3. Stale or malformed state cannot authorize/block a consequential transition without revalidation/recomputation.
4. No shell profile or global ENV is changed.
5. ENV may be projected only into a child process/runtime controlled by PowerPack.

### User Story 9 — Prevent lost updates across simultaneous sessions (Priority: P1)

Two PowerPack sessions can inspect the same state concurrently without silently overwriting one another.

**Acceptance Scenarios**:

1. State records carry a revision/generation.
2. A writer verifies the revision before commit.
3. A conflict reloads/reconciles or fails explicitly rather than silently overwriting a newer write.
4. Readers never observe partial JSON.

### User Story 10 — Diagnose PowerPack consistently (Priority: P1)

A user or homologation script runs `speckit.powerpack.doctor` to inspect component coherence, configuration, state, integration readiness and capability health.

**Acceptance Scenarios**:

1. `doctor` is administrative and does not expand the functional-capability set.
2. Human-readable output identifies actionable failures.
3. `doctor --json` (or equivalent machine-readable mode defined by the plan) exposes stable result codes/fields for automation.
4. Doctor detects stale/malformed state, missing presets, unsupported Spec Kit version, command registration drift, hook/event registration drift and review-backend readiness.

### User Story 11 — Bootstrap through native session events where available (Priority: P2)

When an integration supports native runtime events, PowerPack may validate health/state on `session_start` without requiring the user to invoke a command first.

**Acceptance Scenarios**:

1. Event-based bootstrap is advisory/preparatory and does not silently perform destructive migrations or user-intent changes.
2. Integrations without native events retain equivalent behavior when a PowerPack command/hook is invoked.
3. Event registration is part of compatibility/homologation testing.

### User Story 12 — Support future visual/UI adapters without coupling the runtime (Priority: P2)

A future Copilot Canvas or other UI can read capability/status information and invoke registered PowerPack commands, while the extension remains the workflow authority.

**Acceptance Scenarios**:

1. Core PowerPack operation has no dependency on a canvas/UI.
2. Machine-readable status includes capability ids, readiness, relevant workflow state and recommended actions.
3. UI adapters invoke the same commands/runtime contracts used by CLI/agent workflows.
4. UI-specific allowlists or stage rendering do not redefine PowerPack semantics.

## Persistent Hook-State Model

### Source of truth

Durable workflow state lives under PowerPack-owned mutable project state, conceptually:

```text
.specify/powerpack/state/
    hooks/
        <workflow-or-feature-key>.json
```

Capability specifications MAY define more specific paths while conforming to the common envelope.

### Common envelope

Persistent state SHOULD contain at minimum:

```json
{
  "schema_version": 1,
  "state_type": "<type>",
  "spec": "<active-spec-id>",
  "revision": 7,
  "producer_run_id": "<run-id>",
  "source_artifacts": [
    {
      "path": "<relative-path>",
      "digest": "sha256:<digest>"
    }
  ],
  "validity": "FRESH",
  "status": "<capability-semantic-status>",
  "facts": {},
  "updated_at": "<timestamp>"
}
```

`validity` and semantic `status` are separate dimensions. Capability-specific specifications define their semantic statuses/facts.

### Hook/command consumption

```text
consumer starts
  -> load JSON
  -> validate schema
  -> validate component/state version
  -> validate artifact digests/freshness
  -> validate/reconcile revision if writing
  -> recompute if stale when deterministic
  -> optionally project ENV to controlled child process
  -> execute/report
```

A state-producing post-hook MUST NOT require a pre-existing projected ENV. Separate consumers MUST reload JSON or use the common resolver.

## Capability Registry and Setup Model

Conceptually:

```text
PowerPack Setup
    -> discover environment once
    -> discover capability descriptors
    -> load current config
    -> ask each capability to contribute candidate/default/readiness
    -> validate capability-local constraints
    -> validate cross-capability constraints
    -> present complete candidate
    -> confirm
    -> atomic commit
```

A capability descriptor MUST NOT directly persist partial setup state while the global candidate is being assembled.

## Component Coherence Model

The plan MUST define a machine-readable component-set representation including at least:

```text
bundle identity/version
extension identity/version
required preset identities/versions or compatible ranges
supported Spec Kit range
component-set fingerprint or equivalent
```

A capability that depends on a missing/skewed preset MUST report unavailable/degraded rather than silently recreate the preset outside native lifecycle management.

## Requirements

### Native distribution and composition

- **FR-001**: PowerPack MUST use native Spec Kit lifecycle primitives.
- **FR-002**: The extension SHALL be runtime/config/state authority.
- **FR-003**: Companion presets MAY augment upstream commands but MUST remain thin.
- **FR-004**: A native bundle SHOULD be the preferred release/install composition where supported.
- **FR-005**: PowerPack MUST NOT own Spec Kit CLI installation/upgrade.
- **FR-006**: Component manifests MUST declare explicit compatibility constraints.
- **FR-007**: PowerPack MUST homologate composition with third-party presets and priority/order interactions, not only core+PowerPack in isolation.

### Capability registry and readiness

- **FR-008**: PowerPack MUST maintain a single capability registry/descriptor mechanism used by setup and diagnostics.
- **FR-009**: Setup MUST be registry-driven rather than feature-specific branching for every capability.
- **FR-010**: Installation health and capability state MUST be modeled separately.
- **FR-011**: Optional capability failure MUST NOT disable unrelated ready capabilities without an explicit dependency.
- **FR-012**: Capability status MUST be available in machine-readable form.
- **FR-013**: Functional/admin classification MUST be explicit per capability.

### Component coherence

- **FR-014**: PowerPack MUST verify installed component coherence before relevant capability execution.
- **FR-015**: Installed-by-id alone MUST NOT be treated as proof of version compatibility.
- **FR-016**: Missing/skewed required components return actionable degraded/broken state; no silent self-repair outside native lifecycle.
- **FR-017**: Homologation MUST cover install, update, disable, enable, remove, integration switch/rescaffold and partial bundle failure.

### Environment and review routing

- **FR-018**: Spec Kit machine-readable integration state is authoritative for default/installed integrations.
- **FR-019**: Runtime executable/auth readiness is validated independently.
- **FR-020**: Cross-agent review MUST NOT silently change the default integration.
- **FR-021**: Executor/topology and evidence backend remain separate configuration dimensions.
- **FR-022**: Runtime route invalidation returns `BLOCKED_CONFIGURATION`; no silent fallback.
- **FR-023**: GPT Web remains browserless and Codex-backed unless explicitly superseded by a later accepted capability.
- **FR-024**: GPT Web activation requires validated compatible ChatGPT Project + GitHub evidence readiness.
- **FR-025**: Secrets/credentials MUST NOT be persisted in project config/state.

### Transactional setup

- **FR-026**: Setup/reconfiguration MUST build one complete candidate before commit.
- **FR-027**: Capability modules MUST NOT progressively persist candidate fields.
- **FR-028**: Abort/failure preserves previous valid configuration exactly.
- **FR-029**: Agent and shell setup adapters MUST share the same setup engine.
- **FR-030**: Reconfiguration/reset are distinct; reset requires explicit intent.
- **FR-031**: Configuration writes MUST be atomic/partial-write safe.

### Review execution

- **FR-032**: `max_rounds` is a positive bounded maximum; default is 5.
- **FR-033**: Review stops early when all mandatory gates approve the same immutable snapshot.
- **FR-034**: Prior findings are explicitly accounted for in later rounds.
- **FR-035**: Snapshot-changing fixes invalidate prior approvals.
- **FR-036**: Budget exhaustion never implies approval.

### Persistent state and ENV

- **FR-037**: Durable workflow facts MUST live in project-local JSON, not ENV.
- **FR-038**: PowerPack MUST NOT modify shell profiles/global environment to persist workflow state.
- **FR-039**: ENV projection is allowed only for the current PowerPack-controlled process/child process.
- **FR-040**: A later independent hook/command MUST reload JSON or call the common state resolver; it MUST NOT assume prior hook ENV survived.
- **FR-041**: State records MUST carry schema version, artifact identity/digests, revision and timestamp.
- **FR-042**: Validity/freshness MUST be distinct from capability semantic status.
- **FR-043**: Stale/malformed state cannot authorize/block consequential transitions without validation/recomputation.
- **FR-044**: Persistent state writes MUST use atomic replacement plus conflict/lost-update detection.
- **FR-045**: Concurrent revision conflicts MUST be reconciled or surfaced explicitly, never silently overwritten.
- **FR-046**: Mutable state SHOULD be gitignored by default; the plan defines exact policy.

### Diagnostics and lifecycle

- **FR-047**: PowerPack MUST provide administrative `speckit.powerpack.doctor` or equivalent command.
- **FR-048**: Doctor MUST inspect component coherence, Spec Kit compatibility, command/preset/hook/event registration, configuration schemas, persistent state and capability readiness.
- **FR-049**: Doctor MUST expose machine-readable output for homologation automation.
- **FR-050**: Migration MUST distinguish managed code, config, mutable state and evidence.
- **FR-051**: Update/removal MUST NOT silently delete mutable user/workflow state or historical evidence unless explicitly requested.

### Runtime events and UI adapters

- **FR-052**: PowerPack MAY declare native runtime events for integrations that support them.
- **FR-053**: Native events MUST NOT be required for portable capability correctness.
- **FR-054**: `session_start` MAY validate/bootstrap health/state but MUST NOT silently alter user intent or perform destructive migrations.
- **FR-055**: Machine-readable capability/status output MUST be sufficient for future UI/canvas adapters.
- **FR-056**: UI adapters MUST invoke the same authoritative PowerPack command/runtime contracts and MUST NOT become a second workflow engine.

## Key Entities

- **PowerPack Bundle**
- **PowerPack Extension**
- **PowerPack Companion Preset**
- **Capability Descriptor**
- **Installation Health**
- **Capability State**
- **Component Set / Component Coherence Report**
- **PowerPack Setup State / Candidate Configuration**
- **Environment Capability Snapshot**
- **Review Policy / Review Gate / Review Round**
- **ChatGPT Project Binding**
- **Persistent Hook State**
- **ENV Projection**
- **Doctor Report**
- **UI Status Snapshot**

## Success Criteria

- **SC-001**: Clean supported installations are discoverable through native Spec Kit lifecycle without PowerPack bootstrapping Spec Kit.
- **SC-002**: Removing a companion preset leaves the upstream core command intact.
- **SC-003**: Capability setup remains modular: adding a test capability descriptor requires no duplicate setup engine.
- **SC-004**: Mixed component-version fixtures are detected before capability execution with zero silent skew acceptance.
- **SC-005**: Setup cancellation/failure preserves pre-run configuration in 100% of failure-injection stages.
- **SC-006**: Equivalent agent/shell inputs produce equivalent validated configuration.
- **SC-007**: Review never exceeds `max_rounds` and never reports approval after unresolved budget exhaustion.
- **SC-008**: State produced in one session is recoverable in another after validation without any shell-profile mutation.
- **SC-009**: Concurrent-writer tests produce zero silent lost updates.
- **SC-010**: Stale/malformed state fixtures never authorize consequential transitions without validation/recomputation.
- **SC-011**: `doctor --json` (or equivalent) can drive Linux/WSL/Windows homologation assertions without parsing human prose.
- **SC-012**: Integrations lacking native runtime events still satisfy the same functional capability contracts.
- **SC-013**: A future UI adapter can enumerate capability readiness/recommended actions from machine-readable PowerPack state without embedding PowerPack business logic.

## Assumptions

- SPEC-001 currently limits functional capabilities to `implement-review`.
- Supported Spec Kit versions provide native extensions, presets, hooks/integration state and, where selected, bundles.
- Bundle installation/rollback is not assumed perfectly transactional; PowerPack diagnostics verify the resulting component set.
- Codex and other agents own their installation/authentication.
- Python remains available for the initial portable shell entrypoint.
- Mutable PowerPack state is local workflow state, not automatically a repository collaboration protocol.
- Copilot Canvas and similar visual surfaces are optional agent-specific adapters and may evolve independently from Spec Kit core.

## Non-Goals

- Adding another functional workflow capability in SPEC-002.
- Forking Spec Kit.
- Making presets the main runtime.
- Maintaining permanent copies of upstream skills when composition suffices.
- Automatically switching the default AI integration.
- Persisting credentials or workflow state in shell profiles/global ENV.
- Treating ENV as communication between independent hooks/sessions.
- Making Copilot Canvas or any UI mandatory for PowerPack.
- Automatically synchronizing mutable PowerPack state across machines/repositories.

## Core Invariants

```text
PowerPack lifecycle owner == Specify
```

```text
PowerPack runtime authority == extension
preset responsibility == upstream composition only
```

```text
functional PowerPack capabilities == {implement-review}
```

```text
SETUP_ENGINE == aggregate(CAPABILITY_REGISTRY)
```

```text
installation_health != capability_state
```

```text
component_installed != component_compatible
```

```text
PERSISTENT_WORKFLOW_STATE == project_local_json
ENV == optional_child_process_projection(validated(JSON))
```

```text
independent_hook_or_session
  => reload JSON
  != rely_on_previous_hook_ENV
```

```text
atomic_write + revision_check
  => no_partial_state
  => no_silent_lost_update
```

```text
CONFIG != STATE != EVIDENCE
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
RUNTIME_ROUTE_INVALID
  => BLOCKED_CONFIGURATION
  != SILENT_FALLBACK
```

```text
final_approval
  => all_required_gates_approve_same_immutable_snapshot
```

```text
UI_OR_CANVAS
  => adapter_over_authoritative_runtime
  != second_workflow_engine
```
