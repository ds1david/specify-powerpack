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

## Clarifications

### Session 2026-09-09

- Q: Should `implement-review` keep depending on the PowerPack `speckit.implement` / `speckit.converge` wraps, or be re-based on the upstream Spec Kit commands so the wraps can be removed? → A: Remove both wraps; re-base the `implement-review` prerequisite gate and Phase 1 convergence onto upstream Spec Kit `speckit-implement` / `speckit-converge`. Preserved set stays exactly `{implement-review}`.
- Q: Is the browserless ChatGPT Project + GitHub review path intrinsic to `implement-review` or an optional gate that can be trimmed? → A: Keep it as part of the `implement-review` contract (runtime + `smoke_chatgpt_github_browserless.py` + smoke doc), but remove the exploratory scaffolding: `scripts/homologation/probe_*`, `*.har` dumps, `docs/WEB_GITHUB_HEADLESS_PROBE.md`.
- Q: Should the `powerpack-tools` extension (`doctor`, `update`) be preserved as infrastructure, or do those commands count toward the single-command contract? → A: Preserve `powerpack-tools` intact as runtime infrastructure; the exact-set assertion is scoped to the `powerpack-core` preset only → `{"speckit.implement-review"}`.
- Q: Which installation paths are officially supported and must be validated for the parity contract? → A: `install.sh`, `install.py`, and `install.ps1`, each validated to produce `{"speckit.implement-review"}` for one canonical integration. Full installer×integration matrix is not required as an end-to-end gate.

### PR #15 review (2026-09-09)

- Finding (HIGH, behavioral regression): the first re-based gate accepted *any* non-doc
  change on the branch/worktree, so SPEC-B could be satisfied by SPEC-A's code — contradicting
  `implement-review`'s stated "explicit same-SPEC predecessor is proven". → Resolution:
  **FR-018a** — the delta is scoped to the SPEC via `feature_base_commit` (diff from the
  commit that introduced the SPEC's plan/tasks to HEAD), the working tree is not consulted,
  and a cross-SPEC rejection test is mandatory.

### PR #15 review — round 2 (2026-09-10)

- Finding (HIGH ×2): the SPEC, the prerequisite contract and the runtime had diverged on
  FR-018a. (a) `feature_base_commit` returned the *parent* of the SPEC-introduction commit,
  so a non-doc change bundled into that commit counted as implementation evidence with no
  later commit. (b) checkbox state was read from the working-tree `tasks.md`, so locally
  ticking boxes without committing passed the gate. → Resolution: FR-018a below is the
  single definition — the anchor is the SPEC-introduction commit itself and the delta is
  **strictly after** it; checkbox state is read from `git show HEAD:<feature>/tasks.md`.
  Contract, `speckit.implement-review.md`, `research.md`, `data-model.md`, `quickstart.md`
  and `T025-validation-runbook.md` are aligned to it. Two regression tests are mandatory
  (bundled-code-in-introduction-commit → `NO_IMPLEMENTATION_DELTA`; committed `[ ]` +
  working-tree `[X]` → `TASKS_INCOMPLETE`).

### PR #15 review — round 3 (2026-09-10, live homologation)

- The T025/T051 live browserless round-trip was executed against the PR head (evidence:
  `T025-evidence/`). The mechanism passed (S1–S7, real Codex → ChatGPT Project → GitHub,
  no step failed due to a removed command). The deep review returned `CHANGES_REQUIRED`.
- Finding (HIGH, self-referential gate): `implement_evidence` required **every** `tasks.md`
  checkbox `[X]`, including the T025/T051/T057 homologation tasks — which can only be done
  *after* `implement-review` runs. The SPEC's own committed HEAD could therefore never pass
  its own prerequisite. → Resolution: FR-018a below — a checkbox line tagged `[ACCEPTANCE]`
  is implementation-complete work validated *after* `implement-review` and is **excluded**
  from the prerequisite's checkbox count (`count_implementation_checkboxes`). Homologation
  evidence is then a PR-review concern (the committed `T025-evidence/` + `RESULT.md`), not
  a runtime gate. Regression test: an unchecked `[ACCEPTANCE]` task + all implementation
  boxes `[X]` + a committed code delta → `{"ok": true}`.
- Finding (HIGH): a normal `update` of an already-installed project never removed retired
  removed-command runtimes/config. → Resolution: FR-003 / FR-012 below — `install_support`
  prunes obsolete PowerPack-owned paths and removed-command routing/prerequisite keys on
  every refresh (not a compatibility shim; dead-file removal).
- Findings (MEDIUM ×2): `test_baseline_contract.py` proved the exact-set and
  removed-command-unknown properties only against source/argparse. → Resolution: FR-011 /
  FR-014 — the guard also exercises the real installed command namespace and dispatcher.

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
- **Removed command**: every PowerPack-provided command in the baseline preset that is not
  `speckit.implement-review` — including `speckit.implement` and `speckit.converge` (see
  Clarifications 2026-09-09: the `implement-review` flow is re-based onto the upstream Spec
  Kit commands instead of these wraps).
- **Out of scope for removal**: the upstream Spec Kit workflow commands / agent skills
  (`speckit-plan`, `speckit-tasks`, `speckit-specify`, `speckit-analyze`, `speckit-clarify`,
  `speckit-constitution`, `speckit-checklist`, `speckit-converge`, `speckit-implement`,
  `speckit-taskstoissues`, `graphify`, …) that PowerPack does not own. They live under the
  host project's `.claude/skills/` and are installed by Spec Kit / other tooling, not by
  PowerPack. Nothing in this spec deletes or renames them.
- **Preserved infrastructure (not a product command)**: the `powerpack-tools` extension and
  its `speckit.powerpack-tools.doctor` / `speckit.powerpack-tools.update` commands, plus the
  `bin/powerpack.py` runtime. `doctor` is an operational prerequisite of `implement-review`.
  The extension is kept intact (see Clarifications 2026-09-09); only code paths that exist
  solely for a removed `powerpack-core` command are trimmed from it.

The exact-set assertions in this spec are always scoped to **`powerpack-core` preset
commands** (the `provides.templates` list), never to the `powerpack-tools` extension
namespace and never to the host project's full command or skill inventory.

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

1. **Given** a clean installation and a project whose implementation was completed via
   upstream `speckit-implement`, **When** the re-based `implement-review` prerequisite check
   runs, **Then** it passes without any PowerPack `speckit.implement` receipt.
2. **Given** the `implement-review` flow is executing, **When** it needs to converge or
   re-run implementation for authorized appended work, **Then** it invokes upstream
   `speckit-converge` / `speckit-implement` and that step completes.
3. **Given** the mandatory readiness checks for `implement-review` (including
   `specify-powerpack doctor` and `review status`), **When** they run, **Then** every
   command/runtime they invoke still exists after the cleanup.

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

- One of `install.sh` / `install.py` / `install.ps1` copies legacy content even after preset
  cleanup → the contract is verified against the resulting install state, not only installer
  source.
- A helper or runtime module used by a removed command is also required by `implement-review`
  → it is classified as shared core infrastructure and preserved (see FR-013).
- A removed command name still appears in a completed spec, changelog, ADR, or merged-PR
  record → allowed as `HISTORICAL_REFERENCE` provided it does not imply current support.
- The `implement-review` flow calls convergence / implementation steps internally → after
  re-basing (FR-018) it MUST call upstream Spec Kit `speckit-converge` / `speckit-implement`,
  never the removed PowerPack `speckit.converge` / `speckit.implement` wraps.
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
  and assets, dedicated tests and fixtures, and operational documentation. *(Resolved round
  3, 2026-09-10)* This MUST also hold for an **already-installed project after a normal
  `update`/refresh** — `install_support` MUST prune obsolete PowerPack-owned paths and
  removed-command config keys from the target, not merely stop copying them. This is
  dead-file removal, not a compatibility migration shim (which line "no migration shim is
  provided" in Scope still forbids).
- **FR-004**: After the cleanup, every discovery mechanism PowerPack controls (preset
  registration, manifest, filesystem scan, metadata scan, command generator, or equivalent)
  MUST expose exactly one PowerPack-provided command: `speckit.implement-review`.
- **FR-005**: Every officially supported installation path MUST install only
  `implement-review` as `powerpack-core` command content. The officially supported paths
  (per Clarifications 2026-09-09) are the three entrypoints the README advertises:
  `install.sh` (Linux/WSL/macOS), `install.py` (any platform with Python), and `install.ps1`
  (Windows PowerShell). No installer MAY copy, register, generate, or reference a removed
  command.
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
  `"speckit.implement-review" in commands` is insufficient on its own. *(Resolved round 3)*
  The `installed_powerpack_commands` assertion MUST enumerate the command namespace
  materialised by a real installation composition (preset boundary), not only re-check the
  source preset.
- **FR-012**: Feature flags, aliases, mappings, constants, paths, environment variables,
  registry entries, and routing/prerequisite map entries used exclusively by removed
  commands MUST be removed. This includes removed-command keys in
  `config/default-model-routing.json`, the `prerequisites.json` defaults, and runtime
  prerequisite maps. (Whole config *files* dedicated to a removed command — e.g.
  `config/default-full-cycle.json`, `config/default-technical-debt.json` — are covered by
  FR-003.) The `implement-review` prerequisite entry MUST be re-based onto an upstream
  `speckit-implement` signal (FR-018), not deleted. *(Resolved round 3)* On a normal
  `update`/refresh, `install_support` MUST also strip these removed-command keys from an
  existing target's `model-routing.json` / `prerequisites.json` even without
  `--reset-config`, while preserving keys and files that are not removed-command-specific.
- **FR-013**: Generic infrastructure MUST remain when required by `implement-review`, the
  installation lifecycle, cross-agent support, shared tests, or the reusable PowerPack core.
  The `powerpack-tools` extension and `bin/powerpack.py` runtime remain in scope only for
  removed-command-specific code paths; their shared surface (doctor, model routing, state
  receipts, review status) MUST be preserved. Command removal MUST NOT become an accidental
  core redesign.
- **FR-014**: Removed commands MUST NOT survive through deprecated aliases, redirects,
  hidden copies, fallback implementations, or compatibility wrappers. No deprecation
  compatibility layer is required or permitted. Compliance MUST be verified behaviourally,
  not only by textual search: an automated check MUST invoke a removed command name against a
  clean install and assert unknown-command behaviour at the command registration/dispatch
  layer (not merely that the string is absent from source). *(Resolved round 3)* This check
  MUST drive the real resolver over a materialised install (guarded to skip only when the
  `specify` binary is absent), covering at least `speckit.implement`, `speckit.full-cycle`
  and one `speckit.debt-*`, and assert no `implement-review` side effect.
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
- **FR-018** *(dependency re-basing — resolved 2026-09-09)*: The implementation MUST keep the
  `implement-review` flow operational end to end while removing the `speckit.implement` and
  `speckit.converge` wraps. Specifically: (a) the `implement-review` prerequisite gate MUST
  be satisfiable without a PowerPack `speckit.implement` completion receipt, and the
  `speckit.implement` command template MUST be removed. (b) The `implement-review` Phase 1
  convergence loop (including re-implementation of appended tasks) MUST call upstream
  `speckit-converge` / `speckit-implement`, and the PowerPack `speckit.converge` command
  template MUST be removed. No `speckit.implement` / `speckit.converge` behavior may survive
  as an alias, shim, or hidden copy (FR-014).
- **FR-018a** *(SPEC-scoped predecessor evidence — resolved after PR review, 2026-09-09)*:
  The re-based prerequisite MUST prove an explicit prior implementation **of the active
  SPEC**, not merely "some non-documentation change exists on the branch". It MUST be
  satisfied only when (i) every **implementation** task checkbox in the SPEC's **committed**
  `tasks.md` (read from `HEAD`, not the working tree) is `[X]`, and (ii) a non-documentation
  change has been **committed strictly after** the commit that introduced the SPEC's
  `plan.md`/`tasks.md`, up to `HEAD`. Neither a different SPEC's earlier code change on the
  same (or a re-used) branch nor a non-documentation change bundled into the SPEC's own
  introduction commit MUST satisfy it. A checkbox line tagged **`[ACCEPTANCE]`** is
  implementation-complete work whose validation necessarily runs *after* `implement-review`
  (homologation); it MUST be excluded from the checkbox count in (i), and homologation is
  then proven by PR review over the committed evidence, not by this runtime gate. The
  working tree MUST NOT be consulted for checkbox state or the
  implementation delta (the browserless gate already pins `HEAD == PR head SHA`); it is
  read only to confirm `tasks.md` exists, and — when git is unavailable — for the degraded
  checkbox scan.
  Failure reasons: `MISSING_TASKS`, `TASKS_INCOMPLETE`, `NO_SPEC_BASELINE` (the SPEC's own
  artifacts are not committed yet), `NO_IMPLEMENTATION_DELTA`. Git unavailable ⇒ degrade to
  tasks-only, flagged `git_unavailable`. Automated tests MUST encode the cross-SPEC
  rejection (SPEC-A code must not satisfy SPEC-B's gate) and the `[ACCEPTANCE]` exemption
  (an unchecked `[ACCEPTANCE]` task must not block; a plain unchecked task still does).
- **FR-019**: `install.sh`, `install.py`, and `install.ps1` MUST each be validated to
  produce the same `powerpack-core` command inventory — `{"speckit.implement-review"}` — for
  the canonical integration `codex` (`DEFAULT_INTEGRATION` in `cli.py`). A platform-specific
  installer MAY differ internally but MUST NOT produce a different command set.
  Cross-integration parity (`codex` vs `claude`) is assumed by inspection, not required as an
  end-to-end gate.
- **FR-020** *(browserless review scope — resolved 2026-09-09)*: The browserless ChatGPT
  Project + GitHub review gate (Codex CLI + `~/.codex/auth.json` + GitHub connector,
  read-only) REMAINS part of the `implement-review` contract. Its runtime, the
  `smoke_chatgpt_github_browserless.py` homologation smoke, and
  `docs/CHATGPT_GITHUB_BROWSERLESS_SMOKE.md` MUST be preserved and kept working.
- **FR-021** *(browserless review scope — resolved 2026-09-09)*: Exploratory discovery
  scaffolding for that path MUST be removed — the `scripts/homologation/probe_*` probes,
  captured `*.har` traffic dumps, and `docs/WEB_GITHUB_HEADLESS_PROBE.md`. These are
  historical investigation artifacts, are not exercised by the minimum smoke, and MUST NOT be
  treated as part of the supported contract. A test whose **sole** subject is a removed probe
  MUST be deleted (FR-009); a test covering the preserved smoke or the preserved
  `github_connector_preflight` MUST stay. A test that covers both MUST be split or narrowed
  to the preserved surface, not deleted.
- **FR-022**: Documentation and homologation material for `full-cycle` and the technical-debt
  lifecycle follows the normal removed-command rule (FR-003, FR-007): delete, or convert to
  clearly labelled non-advertising history.

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
  with a valid completed implementation. "Attributable to a removed command" means: the
  failure's root cause is a deleted file, command, config key, or a re-basing change made by
  this feature (verifiable by `git bisect` / reverting the change) — not a pre-existing
  unrelated defect. Zero such failures.
- **SC-004**: `install.sh`, `install.py`, and `install.ps1` each produce an identical
  `powerpack-core` command inventory (`{"speckit.implement-review"}`) for the canonical
  integration — zero divergence across the three entrypoints.
- **SC-005**: The full automated test suite passes, and it includes at least one exact-set
  baseline contract test that fails if a second PowerPack-provided command is added.
- **SC-006**: No installed file belonging exclusively to a removed command is present in the
  clean install state (residual-artifact count == 0).
- **SC-007**: Current-state documentation (README + installation + architecture + agent
  instructions) presents `implement-review` as the only current `powerpack-core` command:
  the README's capability/overview section names exactly one such command, and no
  current-state page lists a removed command as available. Verifiable by inspection of the
  named sections.

## Assumptions

- "001" as the command argument means "work on feature 001" — regenerate this existing spec
  on the standard Spec Kit template and reconcile terminology, not create a new feature.
- The feature directory name stays `specs/001-single-skill-baseline` (no renumbering).
- The unit of removal is the PowerPack-provided preset command. Upstream Spec Kit workflow
  commands / agent skills in the host project's `.claude/skills/` are out of scope and are
  never deleted or renamed by this work.
- `.specify/memory/constitution.md` is still the unpopulated template and imposes no
  concrete constraints on this spec; if it is filled before planning, the plan must re-check.
- Every target project already has upstream Spec Kit `speckit-implement` and
  `speckit-converge` available (Spec Kit ≥ 1.0.0). The re-based `implement-review` flow and
  its evidence gate (FR-018) depend on this; PowerPack does not install those commands.
- The implementation baseline is a recorded commit. The previous draft recorded
  `a825557a0d021e9e9948ad212349bf91d76a619c`; current `main` HEAD is
  `489f5355f7d2b32e50f0c0daa7b6bdb577655338`. The plan MUST record the actual starting SHA
  and explain any inventory delta between `a825557` and the chosen baseline (notably the
  browserless code-review and project-evolution-policy merges #9 and #10).
- The technical-debt lifecycle commands (`debt-create`, `debt-list`, `debt-consult`,
  `debt-start`, `debt-close`), `full-cycle`, `checklist-converge`, `implement`, and
  `converge` are all `REMOVE` — none is a preserved dependency of `implement-review` (the
  review flow is re-based onto upstream Spec Kit for implementation/convergence, per FR-018).
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
    └── speckit.implement-review   (re-based on upstream speckit-implement / speckit-converge)
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
- **R-005 — Platform divergence**: `install.sh` / `install.py` / `install.ps1` generate
  different inventories. *Mitigation*: enforce the same post-install contract on all three
  entrypoints (FR-019, SC-004).
- **R-006 — Breaking `implement-review`**: removing `speckit.implement` / `speckit.converge`
  breaks the review flow's prereq gate and convergence loop unless it is re-based first.
  *Mitigation*: FR-018 — re-base the gate onto upstream `speckit-implement` and the Phase 1
  loop onto upstream `speckit-converge` / `speckit-implement`, verified by User Story 2
  acceptance scenarios, before deleting either wrap.

## Migration Strategy

Intentionally breaking for consumers of removed commands. No deprecation compatibility
layer. Sequence:

1. Record the actual baseline SHA and inventory the preset.
2. Identify shared dependencies; re-base the `implement-review` prerequisite gate and Phase 1
   convergence onto upstream Spec Kit before deleting `speckit.implement` / `speckit.converge`.
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
PowerPack command inventory of exactly `{"speckit.implement-review"}`, with the
`implement-review` flow re-based onto upstream `speckit-implement` / `speckit-converge`, and
implementation, preset registration,
installation, current-state documentation, and smoke-test expectations all describe that
same state.
