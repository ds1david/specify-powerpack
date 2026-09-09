# Feature Specification: Native Plugin Setup and Review Routing

**Feature Branch**: `002-plugin-setup-routing`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Migrate Specify PowerPack toward native Spec Kit extension installation and define first-install setup, reconfiguration, automatic integration/capability detection, local/cross-agent/Codex/GPT Web review routing, compatible ChatGPT Project binding, and configurable automatic review rounds."

## Overview

Evolve Specify PowerPack from a bootstrap-oriented companion CLI into a Spec Kit-native
extension whose installation lifecycle is owned by `specify`, while preserving
`implement-review` as the single functional PowerPack capability established by SPEC-001.

The extension must provide a deterministic setup and reconfiguration flow that discovers the
Spec Kit project's active/default AI integration, all installed integrations, relevant local
CLI/authentication capabilities, and the review routes that are actually executable in the
current environment. The user selects an explicit review strategy and a maximum automatic
review-round budget; PowerPack persists only a fully validated configuration and never
silently changes reviewer or evidence backend at runtime.

The target installation relationship is:

```text
Specify
  -> installs/manages PowerPack extension
       -> administrative setup/reconfiguration
       -> implement-review
```

PowerPack must no longer conceptually own installation or upgrade of Spec Kit itself.

### Dependency on SPEC-001

This specification depends on `001-single-skill-baseline` establishing `implement-review` as
the only functional PowerPack capability. Administrative commands required to configure or
diagnose the extension do not count as additional review/workflow capabilities and therefore
do not violate the SPEC-001 functional baseline.

### Terminology

- **Workflow agent**: the Spec Kit `default_integration` currently driving the project.
- **Installed integration**: an entry in Spec Kit `installed_integrations`; it may be
  available as a secondary integration without being the workflow agent.
- **Active-agent local review**: review performed by the same non-Codex AI CLI currently
  driving the Spec Kit workflow, using the local `implement-review` contract.
- **Codex same-session review**: when Codex is the Spec Kit workflow agent, local review is
  performed in the current Codex workflow/session rather than launching a second reviewer
  merely to simulate independence.
- **Codex cross-agent review**: when another agent drives the Spec Kit workflow and Codex is
  installed/ready as a secondary reviewer, PowerPack invokes Codex as the reviewer while the
  original agent remains responsible for the workflow and fixes.
- **Local backend**: review based on the local repository/SPEC context and the review flow
  already implemented by `implement-review`.
- **GPT Web / ChatGPT Project backend**: the existing browserless Codex-authenticated review
  path that binds to a compatible ChatGPT Project, serializes Project context, and uses the
  GitHub App/connector for immutable PR evidence. It does not mean browser automation.
- **Review gate**: one configured review step in an ordered review plan. Multiple gates may
  be composed; all final approvals must refer to the same immutable final snapshot.
- **Candidate configuration**: a complete proposed configuration held in memory/temporary
  state during setup. It is not active until fully validated and atomically committed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install PowerPack as a native Spec Kit extension (Priority: P1)

A user with an initialized Spec Kit project installs PowerPack through the native extension
manager. PowerPack is registered as an ordinary extension, its managed files are owned by
Spec Kit, and the project is left in a safe `PENDING` setup state until the user intentionally
configures review routing.

**Why this priority**: Native installation is the architectural boundary that allows
PowerPack to evolve with Spec Kit instead of wrapping and managing Spec Kit itself.

**Independent Test**: Install a release or development copy using `specify extension add`,
inspect `specify extension list/info`, verify PowerPack is registered, verify no PowerPack
preset/bootstrap is required for `implement-review`, and verify setup state is pending rather
than partially guessed.

**Acceptance Scenarios**:

1. **Given** an initialized compatible Spec Kit project, **When** PowerPack is installed by
   the native extension manager, **Then** it appears as an enabled installed extension.
2. **Given** a fresh PowerPack installation, **When** no setup has yet been completed,
   **Then** `implement-review` refuses to execute a configured review route and reports that
   PowerPack setup is required.
3. **Given** PowerPack is installed, **When** its installation is inspected, **Then** normal
   operation does not require PowerPack to install, replace, or upgrade the `specify` CLI.
4. **Given** the SPEC-001 baseline, **When** the PowerPack extension is enumerated, **Then**
   `implement-review` remains the only functional review/workflow capability; setup is
   administrative lifecycle functionality.

---

### User Story 2 - Setup detects the real Spec Kit/AI environment (Priority: P1)

A user runs PowerPack setup after installation. PowerPack reads Spec Kit integration state,
detects the workflow agent, detects installed secondary integrations and actual CLI/auth
readiness, and presents only review strategies that are executable or clearly identifies the
explicit action needed to enable an additional strategy.

**Why this priority**: Review routing must be based on authoritative capabilities, not on
hard-coded assumptions, filesystem heuristics, or the user's memory of how the project was
initialized.

**Independent Test**: Exercise fixtures whose `.specify/integration.json` contains Codex as
default, Claude as default with no Codex, and Claude as default with Codex installed. Stub CLI
and authentication availability and assert the resulting capability graph and offered routes.

**Acceptance Scenarios**:

1. **Given** `default_integration = codex`, **When** setup discovers capabilities, **Then**
   Codex same-session local review is offered.
2. **Given** `default_integration = claude` and Codex is not an installed/ready secondary
   integration, **When** setup runs, **Then** active-agent local review is offered and Codex
   cross-agent review is not presented as currently ready.
3. **Given** `default_integration = claude`, Codex is installed as a secondary integration,
   Codex CLI is available and authentication is valid, **When** setup runs, **Then** both
   Claude local and Codex cross-agent review routes are available.
4. **Given** Codex is installed in Spec Kit state but the Codex executable or authentication
   is unavailable, **When** setup evaluates capabilities, **Then** the affected Codex route is
   marked unavailable and cannot be committed as a valid strategy.
5. **Given** a non-default Codex integration, **When** PowerPack performs cross-agent review,
   **Then** the Spec Kit default integration remains unchanged; PowerPack does not silently
   run `specify integration use codex`.

---

### User Story 3 - Configure local, cross-agent, and GPT Web review plans (Priority: P1)

A user chooses the desired review topology from routes supported by the detected environment.
PowerPack can use the active agent for local review, Codex in the same session when Codex is
active, Codex as a cross-agent reviewer when another agent is active, and GPT Web/ChatGPT
Project as an additional Codex-backed evidence gate when all of its prerequisites are valid.

**Why this priority**: This is the core user value of the setup: the same `implement-review`
capability must adapt cleanly to Codex, Claude, and other Spec Kit workflows without hidden
reviewer changes.

**Independent Test**: Build the review plan from representative environments and execute a
mock round. Assert the selected executor/backend pair is honored exactly and that invalid
combinations fail before persistence/execution.

**Acceptance Scenarios**:

1. **Given** a non-Codex workflow agent, **When** the user selects active-agent local review,
   **Then** the existing local `implement-review` semantics execute in that workflow agent.
2. **Given** Codex is the workflow agent, **When** the user selects Codex local review,
   **Then** review executes as Codex same-session review without unnecessarily spawning a
   separate cross-agent reviewer.
3. **Given** Claude is the workflow agent and Codex is ready as a secondary integration,
   **When** the user selects Codex cross-agent local review, **Then** Codex reviews while
   Claude remains the workflow/fix agent.
4. **Given** a Codex-backed local or cross-agent route and GPT Web prerequisites are valid,
   **When** the user adds GPT Web as a review gate, **Then** the ChatGPT Project/GitHub gate
   may execute after earlier configured gates are clean.
5. **Given** a non-Codex active-agent-only route with no Codex reviewer, **When** GPT Web is
   requested, **Then** setup rejects the combination rather than silently introducing Codex.

---

### User Story 4 - GPT Web binding is mandatory and setup is atomic (Priority: P1)

A user chooses a GPT Web review route. PowerPack requires selection and validation of a
compatible ChatGPT Project and GitHub evidence path before any new configuration becomes
active. If the user cancels, cannot bind a compatible Project, rejects confirmation, or any
validation fails, no setup/reconfiguration modification is committed.

**Why this priority**: A partially written GPT Web configuration is operationally dangerous:
it can make reviews appear configured while evidence guarantees are absent.

**Independent Test**: Start from both unconfigured and already configured projects; simulate
cancellation/failure at every wizard stage; compare persisted configuration before and after
byte-for-byte or semantically and assert it is unchanged.

**Acceptance Scenarios**:

1. **Given** GPT Web is selected, **When** no compatible ChatGPT Project is successfully
   bound, **Then** GPT Web cannot become active.
2. **Given** the user cancels Project selection, **When** setup exits, **Then** the persisted
   configuration is exactly the same as immediately before setup began.
3. **Given** an existing valid configuration, **When** GPT Web reconfiguration fails during
   Project/GitHub validation, **Then** the previous valid configuration remains active and
   unchanged.
4. **Given** first-time setup with only the installation-created `PENDING` defaults, **When**
   setup is aborted, **Then** those defaults remain unchanged and no candidate selections are
   persisted.
5. **Given** a selected Project, **When** Project access, context readability, GitHub
   connector readiness, repository authorization, or required evidence access cannot be
   proven, **Then** the candidate is rejected as incompatible and is not committed.

---

### User Story 5 - Configure automatic sequential review rounds (Priority: P1)

During setup the user selects a maximum number of automatic review rounds. `implement-review`
executes configured gates sequentially, carries previous findings forward, fixes authorized
findings through the existing flow, creates a fresh snapshot after changes, and stops early
as soon as all required gates approve the same snapshot.

**Why this priority**: Automated rounds are useful only if they preserve evidence continuity,
terminate when clean, and never transform budget exhaustion into approval.

**Independent Test**: Run deterministic fake reviewers across budgets of 1, 3, and 5 rounds;
assert early completion, previous-finding accounting, snapshot invalidation after fixes, and
`BLOCKED_BUDGET` on unresolved findings at the limit.

**Acceptance Scenarios**:

1. **Given** `max_rounds = 5`, **When** all configured gates approve in round 3, **Then**
   rounds 4 and 5 are not executed.
2. **Given** findings in round N, **When** round N+1 begins after fixes, **Then** every prior
   finding is explicitly revalidated according to the existing review protocol.
3. **Given** code changes after a finding, **When** review resumes, **Then** approvals tied to
   the previous immutable snapshot are invalid and all required final gates approve the new
   final snapshot.
4. **Given** the configured round budget is exhausted with unresolved findings or an
   unapproved mandatory gate, **When** the flow terminates, **Then** it returns
   `BLOCKED_BUDGET`, never `APPROVED`.

---

### User Story 6 - Reconfigure PowerPack at any time (Priority: P2)

A user can rerun setup whenever the environment or review policy changes. Setup shows the
current configuration, rediscovers the current Spec Kit/CLI capabilities, allows selective
changes, validates the complete resulting candidate, and atomically replaces the prior
configuration only after success and confirmation.

**Why this priority**: Spec Kit integrations, available CLIs, authentication, Project
bindings, and review policies evolve during project life; configuration cannot be a one-time
installation event.

**Independent Test**: Start with a valid Claude+Codex-cross configuration, reconfigure only
`max_rounds`, then reconfigure to GPT Web, then remove Codex from the environment and verify
runtime drift detection blocks rather than silently falls back.

**Acceptance Scenarios**:

1. **Given** PowerPack is already `READY`, **When** setup is executed again, **Then** it
   behaves as reconfiguration rather than reporting "already configured".
2. **Given** only `max_rounds` is changed, **When** the complete candidate remains valid,
   **Then** all unspecified valid settings are preserved.
3. **Given** the user aborts reconfiguration, **When** the command exits, **Then** the prior
   configuration is preserved exactly.
4. **Given** the environment changed after configuration, **When** `implement-review` starts,
   **Then** PowerPack rediscovers sufficient capabilities and blocks stale/invalid routing
   with `BLOCKED_CONFIGURATION` instead of changing reviewer/backend automatically.

---

### User Story 7 - Run the same setup engine from an AI command or shell (Priority: P2)

A user can configure PowerPack interactively from the installed AI integration using the
PowerPack setup command, or from a normal shell using the extension's Python setup entrypoint.
Both surfaces support parameters/non-interactive automation and invoke the same underlying
setup engine and validation rules.

**Why this priority**: Interactive agent workflows and repeatable CI/homologation need the
same semantics. Two separate setup implementations would drift immediately.

**Independent Test**: Feed equivalent arguments through both adapters and assert identical
candidate configuration, validation result, exit semantics, and persisted output.

**Acceptance Scenarios**:

1. **Given** an active AI CLI, **When** the user invokes the extension command with no
   arguments, **Then** it starts the interactive setup flow.
2. **Given** an active AI CLI, **When** setup parameters are supplied through `$ARGUMENTS`,
   **Then** they are parsed as explicit setup intent and validated against discovered
   capabilities.
3. **Given** a shell, **When** the user invokes the installed extension Python setup script
   with complete parameters, **Then** setup can run non-interactively without a global
   `specify-powerpack` CLI dependency.
4. **Given** incomplete parameters and an interactive TTY, **When** the shell entrypoint is
   used, **Then** missing choices are collected by the same wizard semantics.
5. **Given** equivalent requested settings, **When** the AI command and shell entrypoint run
   separately against equivalent environments, **Then** they produce equivalent persisted
   configuration.

### Edge Cases

- `default_integration` is missing or `.specify/integration.json` is unreadable: setup fails
  closed and does not guess the workflow agent from `.claude`, `.agents`, or other folders.
- `installed_integrations` says Codex is installed but the binary is absent: Codex routes are
  unavailable until actual CLI readiness is restored.
- Codex CLI exists but authentication is expired/missing: local cross-agent capability that
  requires authenticated Codex is unavailable; GPT Web is always unavailable.
- A user asks setup to install Codex as a secondary Spec Kit integration: PowerPack may show
  the exact `specify integration install codex` action and may offer to execute it only after
  explicit confirmation; it must never change Spec Kit integrations silently.
- Codex is a non-default integration: Spec Kit need not register the PowerPack extension
  command into Codex for cross-agent review; the active/default agent invokes the PowerPack
  runtime, which uses Codex CLI as a secondary reviewer.
- The default integration changes after setup: runtime rediscovery decides whether the
  configured route is still valid; no silent fallback occurs.
- GPT Web Project discovery returns zero, multiple ambiguous matches, inaccessible Projects,
  or a Project without usable GitHub evidence: no GPT Web candidate is committed.
- Setup is interrupted after user selections but before final commit: persistent
  configuration remains unchanged.
- Atomic rename/write fails: the previous configuration remains recoverable/active and setup
  reports failure.
- `max_rounds` is zero, negative, non-numeric, or above the supported safety limit: candidate
  validation fails before commit.
- A gate approves, a later gate finds a defect, and fixes change HEAD: all approvals for the
  previous snapshot are invalidated and the new round restarts the required final gate set.
- Extension update changes config schema: migration must produce a complete validated
  candidate and preserve the prior config if migration cannot complete safely.

## Requirements *(mandatory)*

### Functional Requirements

#### Native extension installation and ownership

- **FR-001**: PowerPack MUST be installable as a native Spec Kit extension using the
  officially supported extension lifecycle (`add`, `list/info`, `update`, `enable`,
  `disable`, `remove`) and MUST declare an explicit supported `speckit_version` range in its
  extension manifest.
- **FR-002**: Normal PowerPack installation MUST NOT install, replace, downgrade, or upgrade
  Spec Kit. The user/Spec Kit owns the `specify` CLI lifecycle.
- **FR-003**: The native extension MUST expose `implement-review` under the extension
  namespace (target command: `speckit.powerpack.implement-review`) and MUST NOT require a
  PowerPack preset merely to provide this capability.
- **FR-004**: The extension MUST expose an administrative setup command (target command:
  `speckit.powerpack.setup`) without treating setup as an additional functional skill in the
  SPEC-001 baseline.
- **FR-005**: A fresh extension installation MUST materialize only safe defaults and a setup
  state equivalent to `PENDING`; it MUST NOT guess or activate a reviewer/backend before
  capability discovery and user selection.
- **FR-006**: Because the current Spec Kit extension API does not provide a stable mandatory
  post-install interactive `on_install` wizard contract, PowerPack MUST NOT depend on such a
  hook. Installation documentation/output and `implement-review` readiness behavior MUST
  direct an unconfigured user to `speckit.powerpack.setup`.
- **FR-007**: Invoking `implement-review` while setup is not `READY` MUST fail closed with an
  actionable setup requirement; it MUST NOT generate a default review route implicitly.

#### Environment and capability discovery

- **FR-008**: PowerPack MUST use `.specify/integration.json` (or an equivalent stable Spec Kit
  machine-readable interface when the supported version provides one) as the authority for
  `default_integration`, `installed_integrations`, and relevant integration state. Agent
  filesystem directories MUST NOT be the primary source of truth.
- **FR-009**: Setup MUST detect the current workflow agent from `default_integration` and
  MUST distinguish it from secondary installed integrations.
- **FR-010**: Setup MUST validate real runtime capabilities separately from Spec Kit
  registration. For Codex routes this includes, as applicable: Codex present in the relevant
  installed-integration state, Codex CLI executable availability, and usable Codex
  authentication.
- **FR-011**: Setup MUST construct a capability model before presenting/accepting review
  strategies. A user-supplied parameter expresses intent but MUST NOT bypass capability
  validation.
- **FR-012**: When a requested optional capability requires adding Codex as a secondary Spec
  Kit integration, PowerPack MUST NOT perform that integration change silently. It MAY offer
  the explicit action only with user confirmation; aborting/rejecting that action leaves the
  pre-setup PowerPack configuration unchanged.
- **FR-013**: PowerPack MUST NOT change `default_integration` merely to execute a cross-agent
  Codex review.

#### Review topology and backend model

- **FR-014**: Review routing MUST model executor/topology separately from evidence backend;
  the implementation MUST NOT collapse `local`, `cross-agent`, `Codex`, and `GPT Web` into a
  single mutually exclusive enum whose combinations are implicit.
- **FR-015**: When `default_integration != codex`, PowerPack MUST support active-agent local
  review using the existing local `implement-review` flow, provided the active integration
  can execute the command/runtime contract.
- **FR-016**: When `default_integration == codex`, PowerPack MUST support Codex same-session
  local review and MUST NOT spawn a second Codex process solely to simulate cross-agent
  independence when same-session was selected.
- **FR-017**: When `default_integration != codex` and Codex is a ready secondary reviewer,
  PowerPack MUST support Codex cross-agent local review while leaving the workflow/fix agent
  unchanged.
- **FR-018**: PowerPack MAY support an ordered list of review gates. Earlier local/cross-agent
  gates SHOULD run before the more expensive GPT Web/ChatGPT Project gate when both are
  configured. All mandatory final gates MUST approve the exact same final immutable snapshot.
- **FR-019**: PowerPack MUST NOT silently change the configured reviewer, executor topology,
  gate order, or backend because one becomes unavailable. Runtime invalidation returns
  `BLOCKED_CONFIGURATION` with an actionable reconfiguration path.

#### GPT Web / ChatGPT Project contract

- **FR-020**: GPT Web review MUST use the existing browserless ChatGPT Project + GitHub
  evidence flow. This specification MUST NOT introduce Chrome, Playwright, CDP,
  ChatGPT-Web2API, copied browser profiles, or copied web-session cookies as a fallback.
- **FR-021**: GPT Web MUST be available only on a Codex-backed route: Codex same-session or
  Codex cross-agent. A non-Codex active-agent route MUST NOT directly activate GPT Web unless
  a future specification adds a separately validated provider.
- **FR-022**: `backend == chatgpt-project` MUST imply a successfully validated compatible
  ChatGPT Project binding. PowerPack MUST NOT persist an active GPT Web backend with a null,
  missing, ambiguous, or incompatible Project.
- **FR-023**: Before a ChatGPT Project binding can be committed, PowerPack MUST validate at
  minimum: current Codex-authenticated account can access the Project; Project identity is
  uniquely resolved; required Project context is readable; the GitHub App/connector is
  ready; the target repository is authorized/accessibly resolvable; and the required review
  evidence path can be obtained.
- **FR-024**: If GPT Web is selected and Project discovery/binding is aborted or any
  compatibility validation fails, setup/reconfiguration MUST commit no new configuration.
- **FR-025**: Project metadata needed for deterministic rebinding MAY be persisted, but raw
  Codex/ChatGPT tokens, cookies, OAuth secrets, or equivalent credentials MUST NOT be stored
  in the project configuration.

#### Transactional setup and persistence

- **FR-026**: Setup and reconfiguration MUST be transactional: load current configuration,
  construct a complete candidate, apply requested selections in candidate state, validate
  the complete candidate, obtain final confirmation when interactive, and only then commit.
- **FR-027**: Before final commit, setup MUST NOT progressively persist executor, backend,
  Project binding, round budget, or other candidate fields.
- **FR-028**: User cancellation, explicit abort, rejected confirmation, invalid parameter,
  capability failure, Project/GitHub validation failure, or other setup error MUST preserve
  the exact previously valid configuration. For first-time setup, the installation-created
  `PENDING` defaults remain unchanged.
- **FR-029**: Configuration persistence MUST use an atomic replacement strategy or equivalent
  mechanism that prevents a partially written candidate from becoming the active config.
- **FR-030**: Setup MUST distinguish `PENDING`, `READY`, and failure/blocked execution state;
  transient setup failures MUST NOT overwrite a previously `READY` configuration with a
  failed candidate.
- **FR-031**: Environment-owned facts such as current `default_integration` and
  `installed_integrations` MUST be rediscovered from Spec Kit rather than duplicated as
  PowerPack authority. PowerPack persists the chosen review policy/route, not an independent
  competing integration registry.

#### Setup and reconfiguration interfaces

- **FR-032**: PowerPack MUST allow setup/reconfiguration at any time. Running the setup
  command against an already configured project MUST enter reconfiguration semantics rather
  than fail merely because configuration exists.
- **FR-033**: The AI-agent command `speckit.powerpack.setup` MUST support interactive setup
  and MUST consume command arguments (`$ARGUMENTS` or the integration-equivalent parameter
  channel) for explicit/non-interactive configuration intent where the active integration
  supports arguments.
- **FR-034**: PowerPack MUST provide a shell/command-line setup entrypoint that does not
  require the legacy global `specify-powerpack` CLI. For the first native-extension
  implementation, the canonical portable entrypoint SHALL be the extension-owned Python
  script, conceptually:
  `python .specify/extensions/powerpack/scripts/python/setup.py [options]`.
- **FR-035**: The AI command adapter and shell Python adapter MUST invoke the same setup
  engine for discovery, candidate construction, validation, persistence, and result codes;
  there MUST NOT be two independently implemented wizards.
- **FR-036**: The shell entrypoint MUST support fully non-interactive configuration when all
  required parameters are supplied and MUST support interactive prompting for missing choices
  when a TTY is available.
- **FR-037**: Reconfiguration SHOULD support selective changes (for example only
  `max_rounds`) while retaining unspecified prior values only when the resulting complete
  candidate remains valid in the newly discovered environment.
- **FR-038**: Resetting/removing PowerPack configuration MUST be a distinct explicit action;
  ordinary reconfiguration MUST NOT imply reset or deletion of existing valid bindings.
- **FR-039**: Interactive reconfiguration MUST display the current effective PowerPack review
  policy and the newly discovered capabilities before final confirmation.

#### Automatic round budget and review execution

- **FR-040**: Setup MUST ask for/configure a **maximum automatic review-round budget**, not a
  mandatory exact number of rounds. The product default SHALL be `5` unless a later accepted
  specification changes it.
- **FR-041**: `max_rounds` MUST be a positive bounded integer. The technical plan MUST define
  the supported upper bound and validate it consistently across AI-command and shell setup
  adapters.
- **FR-042**: `implement-review` MUST stop early as soon as all configured mandatory gates
  approve the same current immutable snapshot; unused budget MUST NOT trigger redundant
  reviews.
- **FR-043**: Every round after the first MUST account for findings from the prior round
  according to the existing review protocol (for example resolved, still present,
  superseded, or invalidated with evidence). Findings MUST NOT silently disappear from
  continuity accounting.
- **FR-044**: Any implementation/fix that changes the reviewed snapshot MUST invalidate
  approvals tied to the prior snapshot and require the configured final gate set to evaluate
  the fresh snapshot.
- **FR-045**: Exhausting `max_rounds` with unresolved findings, blocked evidence, or an
  unapproved mandatory gate MUST terminate as `BLOCKED_BUDGET` or the more specific blocking
  state defined by the existing protocol; it MUST NOT be converted into approval.
- **FR-046**: The local review path, whether active-agent or Codex same-session/cross-agent,
  MUST preserve the existing `implement-review` convergence, quality-gate, finding repair,
  and fresh-review semantics unless explicitly superseded by a later specification.

#### Drift, migration, update, and removal

- **FR-047**: Before every `implement-review` execution, PowerPack MUST rediscover enough
  environment/capability state to prove the configured route remains executable. Stale
  configuration fails closed and recommends setup/reconfiguration.
- **FR-048**: Changing the Spec Kit default integration MUST NOT automatically rewrite
  PowerPack review policy. On the next execution/setup, PowerPack revalidates the configured
  route against the new environment and either keeps it (if still valid) or blocks for
  explicit reconfiguration.
- **FR-049**: Migration from legacy PowerPack configuration MUST distinguish managed runtime,
  mutable user configuration, ChatGPT Project binding metadata, and generated review
  evidence. Migration MUST NOT silently destroy valid configuration or historical review
  artifacts.
- **FR-050**: An extension update that requires config-schema migration MUST apply the same
  candidate/validate/atomic-commit rule. A failed migration MUST leave the previous
  recoverable configuration intact and report an actionable incompatibility.
- **FR-051**: Extension removal/update MUST treat generated review evidence separately from
  extension-managed code. Removing or replacing managed extension files MUST NOT silently
  delete historical review evidence unless the user explicitly requests data deletion.

### Key Entities *(include if feature involves data)*

- **PowerPack Setup State**: lifecycle state (`PENDING` or `READY`), configuration schema
  version, and metadata needed to determine whether `implement-review` may start.
- **Environment Capability Snapshot**: transient discovery result containing current Spec Kit
  default integration, installed integrations, CLI availability, auth/readiness facts, and
  supported route combinations. It is evidence for setup/runtime validation, not an
  independent persistent integration registry.
- **Review Policy**: user-selected ordered review gates, executor/topology choices, backend
  choices, `max_rounds`, and early-stop behavior.
- **Review Gate**: an ordered unit such as active-agent/local, Codex same-session/local,
  Codex cross-agent/local, or Codex-backed ChatGPT Project/GitHub review.
- **ChatGPT Project Binding**: non-secret stable identity metadata for the explicitly selected
  compatible Project plus enough validation metadata to re-check readiness; credentials stay
  in the Codex/auth provider store.
- **Candidate Configuration**: temporary complete proposed setup state used to guarantee
  transactional validation and no partial persistence.
- **Review Round**: one attempt against an immutable snapshot, linked to prior findings and
  the configured gate sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of clean supported installations can be identified by `specify extension
  list/info` as an installed PowerPack extension without requiring PowerPack to bootstrap the
  Spec Kit CLI.
- **SC-002**: In automated capability fixtures for Codex-default, non-Codex-default, and
  non-Codex+secondary-Codex environments, setup offers exactly the valid configured review
  route set and zero known-invalid selectable routes.
- **SC-003**: Across cancellation/failure injection at every setup stage, persisted
  configuration after the failed/aborted run equals the configuration before setup began in
  100% of cases.
- **SC-004**: GPT Web can never reach `READY` in automated tests without a validated compatible
  ChatGPT Project and GitHub evidence path; all missing/incompatible binding cases fail before
  commit.
- **SC-005**: Equivalent settings submitted through the AI-agent setup command and shell
  Python setup entrypoint produce semantically identical configuration and validation results
  in 100% of cross-interface contract tests.
- **SC-006**: A configured route whose required CLI/integration/auth capability disappears is
  blocked on the next review attempt with zero silent fallback events in the contract suite.
- **SC-007**: For `max_rounds = N`, automated review never executes more than N rounds, stops
  immediately after all mandatory gates approve a common snapshot, and never reports approval
  after budget exhaustion with unresolved findings.
- **SC-008**: Cross-agent review leaves Spec Kit `default_integration` unchanged in all
  supported cross-agent tests.
- **SC-009**: Extension update/reconfiguration failure tests preserve the previous valid
  configuration and historical review evidence with zero partial active configurations.

## Assumptions

- SPEC-001 has removed or re-based unrelated PowerPack capabilities so `implement-review` is
  the only functional capability being migrated/configured here.
- The supported Spec Kit version exposes native extensions and machine-readable integration
  state including `default_integration` and `installed_integrations`.
- Spec Kit may register enabled extension commands only for the current/default integration;
  PowerPack cross-agent Codex review therefore uses Codex as a secondary CLI reviewer and does
  not require switching the Spec Kit default integration or registering the PowerPack command
  into non-default Codex.
- Codex and any other external reviewer CLI remain separately installable/authenticated tools;
  PowerPack detects readiness but does not own user credentials.
- The existing browserless ChatGPT Project/GitHub review provider and Deep Review evidence
  protocol are preserved and adapted into the native extension runtime rather than replaced.
- Python remains available in supported installation environments. The extension-owned Python
  setup script is the first portable shell entrypoint until/unless a future stable Spec Kit
  extension API provides a native extension subcommand execution mechanism.
- Interactive setup defaults to `max_rounds = 5` and early stop on common clean approval.
- Installation may create a default `PENDING` configuration as part of extension-managed
  files. "No modification on abort" means setup/reconfiguration leaves persistent state
  exactly as it existed immediately before that setup invocation.

## Non-Goals

- Adding new functional PowerPack review/workflow skills beyond `implement-review`.
- Forking or modifying Spec Kit to add an `on_install` hook or custom extension CLI
  subcommand.
- Automatically switching the user's default Spec Kit AI integration to Codex.
- Automatically installing a secondary Codex integration without explicit user consent.
- Implementing browser automation for GPT Web.
- Persisting ChatGPT/Codex/GitHub credentials in repository configuration.
- Preserving the legacy `specify-powerpack` CLI as a runtime requirement; it may remain
  temporarily only for development/migration tooling until separately removed.
- Making every installed Spec Kit integration a review executor. This SPEC defines the active
  agent plus Codex-backed routes; additional cross-agent reviewers require explicit future
  capability work.

## Core Invariants

```text
PowerPack lifecycle owner == Specify
```

```text
functional PowerPack capabilities == {implement-review}
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
AI_SETUP_ADAPTER and SHELL_SETUP_ADAPTER
  => SAME_SETUP_ENGINE
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
