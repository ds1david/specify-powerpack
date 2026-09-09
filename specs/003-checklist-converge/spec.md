# Feature Specification: Checklist Convergence Capability

**Feature Branch**: `003-checklist-converge`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Add checklist-converge as a new PowerPack capability based on the useful behavior of the removed legacy skill, integrate it with native Spec Kit checklist/tasks hooks, persist cross-session checklist state in JSON, exploit the active AI agent's available tools without a fixed Spec Kit tool allowlist, and converge requirements-quality gaps without inventing user intent."

## Overview

Add `checklist-converge` as a deliberately new PowerPack functional capability. It may reuse semantic lessons from the historical implementation removed by SPEC-001, but MUST NOT restore the removed preset/runtime architecture or classify the reintroduction as a bug fix.

The target command is:

```text
speckit.powerpack.checklist-converge
```

The capability integrates with the native Spec Kit checklist/tasks lifecycle:

```text
before_checklist
    -> capture checklist inventory/fingerprints

speckit.checklist
    -> upstream checklist behavior remains authoritative

after_checklist
    -> compare delta
    -> analyze custom requirements-quality checklist state
    -> persist JSON
    -> CLEAN | CONVERGENCE_REQUIRED | CLARIFICATION_REQUIRED | BLOCKED_DECISION

explicit checklist-converge when applicable
    -> evaluate
    -> repair deterministic requirements gaps only
    -> re-evaluate
    -> persist updated state

before_tasks
    -> load latest valid JSON
    -> enforce REQUIRED checklist gates
    -> warn for ADVISORY gates
    -> ignore IGNORED gates
```

`checklist-converge` evaluates requirements-writing quality, not application correctness. Application code and tests MUST NOT be used as evidence that a checklist item is satisfied.

### Relationship to SPEC-001

SPEC-001 intentionally established the baseline:

```text
functional PowerPack capabilities == {implement-review}
```

SPEC-003 explicitly proposes the new accepted set:

```text
functional PowerPack capabilities == {
  implement-review,
  checklist-converge
}
```

This is a new capability, not a defect correction.

### Independence and compatibility with SPEC-002

SPEC-003 is independently reviewable and mergeable against `main`. It MUST NOT require SPEC-002 to be merged first.

This specification therefore defines all capability-specific behavioral contracts it needs: JSON persistence semantics, freshness, concurrency expectations, hook behavior, tool-effect boundaries, status model and machine-readable output.

If SPEC-002's shared PowerPack capability registry/state/doctor infrastructure is present, the implementation SHOULD reuse those common services instead of duplicating them. If it is not yet present, SPEC-003 remains implementable with a local capability-specific adapter that conforms to the same contracts and can later migrate without changing user-visible semantics.

## Historical Semantics Preserved

The removed historical skill is reference material only. These semantics remain useful:

1. Checklist items are tests of **requirements-writing quality**.
2. Authority order is:

```text
constitution
> explicit user decisions
> spec
> plan
> supporting requirements/design docs
> tasks
> checklist
```

3. Every evaluated item has exactly one classification:
   - `SATISFIED`
   - `RESOLVABLE_GAP`
   - `BLOCKED_DECISION`
   - `INVALIDATED`
   - `STRUCTURAL_GAP`
4. Deterministic documentation gaps may be repaired.
5. New product/security/UX/business/compliance/architecture/operations intent MUST NOT be invented.
6. Application code/tests MUST NOT be modified.
7. Requirements/design changes after `tasks.md` exists make downstream tasks stale; `tasks.md` is not silently rewritten.

The legacy PowerPack receipt prerequisite is intentionally not preserved.

## Architectural Decisions

### AD-001 — Managed scope is custom reviewer checklists

The capability manages custom requirements-quality checklists for the active feature. The built-in `checklists/requirements.md` used by upstream specify/clarify quality flow is excluded from PowerPack mutation by default.

### AD-002 — Direct invocation is valid without legacy receipts

A user may explicitly invoke `speckit.powerpack.checklist-converge` when one active SPEC and at least one applicable custom checklist are resolvable. Native lifecycle context is useful but no historical `COMPLETED` receipt is required.

### AD-003 — Identify the exact checklist run delta

PowerPack SHOULD use native `before_checklist` and `after_checklist` hooks:

```text
before_checklist
    -> inventory custom checklist paths
    -> hash files/items

after_checklist
    -> compare inventory
    -> identify created/modified checklist files
    -> identify new/changed item fingerprints
```

The implementation MUST NOT rely only on filesystem modification time if deterministic before/after comparison is available.

### AD-004 — Post-checklist analysis is requirements-read-only

`after_checklist` MAY write PowerPack mutable state and report/recommend next actions, but MUST NOT modify authoritative requirements/design documents. Documentation repair requires explicit `checklist-converge` invocation.

### AD-005 — Checklist participation policy controls gating

Each applicable custom checklist has a participation mode:

```text
REQUIRED
ADVISORY
IGNORED
```

Semantics:

```text
REQUIRED + unresolved consequential finding
    -> before_tasks blocks

ADVISORY + unresolved finding
    -> warn/recommend convergence; do not block solely for this checklist

IGNORED
    -> no workflow-gating effect
```

The technical plan defines the project default and explicit override mechanism.

### AD-006 — Unchecked does not mean defective

A newly generated item is normally `[ ]` because reviewer evaluation is pending.

```text
unchecked item != requirements gap
```

Tags such as `[Gap]`, `[Clarity]`, `[Consistency]`, `[Coverage]`, `[Ambiguity]` or similar are analysis signals, not final classifications by themselves.

### AD-007 — Item identity includes a content fingerprint

Checklist item ids such as `CHK007` are not enough because content can change while the id stays stable.

Persistent item identity includes at least:

```text
checklist path
item id
normalized content fingerprint
classification
evidence/reason
```

Fingerprint mismatch invalidates the previous item evaluation.

### AD-008 — Validity and semantic status are separate dimensions

State MUST model at least:

```text
validity:
  FRESH | STALE | INVALID

semantic_status:
  NOT_EVALUATED
  CLEAN
  CONVERGENCE_REQUIRED
  CLARIFICATION_REQUIRED
  BLOCKED_DECISION
  STRUCTURAL_GAPS_REMAIN
  CONVERGED
  CONVERGED_WITH_STALE_TASKS
  BLOCKED_NO_PROGRESS
  BLOCKED_BUDGET
```

A state can be semantically `CONVERGED` but operationally `STALE` after source artifacts change.

### AD-009 — JSON is the durable authority; ENV is never cross-hook authority

Persistent state is project-local JSON, conceptually:

```text
.specify/powerpack/state/checklist-state.json
```

Independent hooks, commands, sessions and agents MUST reload and validate JSON. They MUST NOT assume an ENV value exported by an earlier hook survives into a later hook or parent agent process.

ENV MAY only be projected into a PowerPack-controlled current/child process when useful.

### AD-010 — Persistent writes prevent partial state and silent lost updates

State MUST include a revision/generation field. Writes use atomic replacement plus conflict detection:

```text
read revision N
compute candidate
verify current revision still N
commit N+1
or reload/reconcile/fail explicitly
```

### AD-011 — Clarification forms a closed re-evaluation loop

When new authoritative intent is required:

```text
CLARIFICATION_REQUIRED
  -> obtain explicit user decision / appropriate clarify flow
  -> authoritative artifact changes
  -> old analysis becomes STALE
  -> re-analyze
  -> CLEAN | CONVERGENCE_REQUIRED | BLOCKED...
```

Clarification MUST NOT automatically mark the checklist converged without re-evaluation.

### AD-012 — Agent tools are governed by effects, not a fixed tool-name allowlist

PowerPack MUST NOT impose a portable hard-coded subset of named tools merely because one Spec Kit integration exposes those names.

Conceptually:

```text
available_tools =
    agent_exposed_tools
    ∩ environment_allowed_tools
    ∩ operation_appropriate_tools
```

The skill MAY use available native search, semantic retrieval, file operations, structured editing, shell, subagents, MCP/context retrieval, safe parallel analysis or external read-only evidence where appropriate.

Allowed effects remain constrained:

```text
READ_LOCAL              allowed
SEARCH_LOCAL            allowed
READ_REQUIREMENTS       allowed
WRITE_REQUIREMENTS      allowed only for deterministic authorized repairs
EXECUTE_READ_ONLY       allowed when safe/relevant
EXTERNAL_READ           conditional and evidence-only
WRITE_APPLICATION       forbidden
WRITE_TESTS             forbidden
REMOTE_WRITE            forbidden
DESTRUCTIVE_OPERATION   forbidden
NEW_PRODUCT_INTENT      forbidden
```

More tools do not increase decision authority or mutation scope.

### AD-013 — External evidence cannot create local product intent

External web/MCP evidence MAY support an explicitly referenced standard, contract, regulation or dependency. It MUST NOT override local authority or supply missing product/security/business decisions.

### AD-014 — Safe parallel analysis is allowed

Subagents/workers MAY evaluate disjoint checklist items in parallel when supported. All workers use the same authority/classification contract. Concurrent mutation of the same authoritative artifact or state record MUST be serialized or conflict-detected.

### AD-015 — Convergence is bounded and detects no progress

Convergence has its own `max_convergence_passes`, independent from `implement-review.max_rounds`. The exact default and upper bound are defined in the technical plan.

Each pass records unresolved fingerprints/classifications. Equivalent unresolved state across the plan-defined no-progress threshold returns:

```text
BLOCKED_NO_PROGRESS
```

Budget exhaustion returns:

```text
BLOCKED_BUDGET
```

Neither outcome implies convergence.

### AD-016 — Machine-readable state supports future UI/canvas integration

The capability MUST expose machine-readable status sufficient for a future adapter to show:

- checklist participation mode;
- validity;
- semantic status;
- counts by classification;
- clarification/blocking state;
- `TASKS_STALE`;
- recommended next action;
- `speckit.powerpack.checklist-converge` command id when applicable.

Any Canvas/UI adapter is optional and MUST call the same authoritative PowerPack runtime/command rather than implement convergence logic itself.

## User Scenarios & Testing

### User Story 1 — Analyze the checklist generated by the current run (Priority: P1)

After upstream `speckit.checklist`, PowerPack identifies exactly what changed and persists a read-only semantic analysis.

**Acceptance Scenarios**:

1. `before_checklist` and `after_checklist` determine created/modified checklist files/items.
2. Appending to an existing checklist identifies changed/new items rather than treating every historical item as newly generated.
3. The built-in `requirements.md` alone does not become a managed custom checklist.
4. The analyzer modifies no requirements/design documents.
5. Persisted state is recoverable in a later session after freshness validation.

### User Story 2 — Recommend convergence only when it has useful work (Priority: P1)

PowerPack distinguishes pending reviewer questions from actionable requirements gaps.

**Acceptance Scenarios**:

1. An unchecked item alone does not yield `CONVERGENCE_REQUIRED`.
2. Deterministic gaps grounded in existing authority yield `CONVERGENCE_REQUIRED`.
3. Missing new intent yields `CLARIFICATION_REQUIRED` or `BLOCKED_DECISION`.
4. Clean state does not recommend redundant convergence.

### User Story 3 — Repair deterministic documentation gaps (Priority: P1)

Explicit `checklist-converge` evaluates each item, repairs deterministic requirements gaps, re-evaluates and updates reviewer checkbox state only when justified.

**Acceptance Scenarios**:

1. Every evaluated item receives exactly one allowed classification.
2. `RESOLVABLE_GAP` repairs use existing authoritative intent only.
3. Repaired items are re-evaluated before `[x]` is written.
4. Checklist wording/format is preserved except justified checkbox/status metadata.
5. Application code/tests/build/deployment artifacts are never modified.

### User Story 4 — Stop for new decisions instead of inventing intent (Priority: P1)

When existing authority cannot resolve a finding, the capability blocks and reports the decision needed.

**Acceptance Scenarios**:

1. New product/UX/security/business/compliance/architecture/operations intent is never synthesized as authority.
2. Richer agent tools do not change that rule.
3. After an explicit decision changes requirements, old analysis becomes stale and is re-evaluated.

### User Story 5 — Gate tasks according to checklist participation policy (Priority: P1)

`before_tasks` loads the latest valid state and enforces REQUIRED checklists only.

**Acceptance Scenarios**:

1. REQUIRED unresolved consequential findings block task generation with an actionable next step.
2. ADVISORY unresolved findings warn but do not block solely because of that checklist.
3. IGNORED checklists do not gate tasks.
4. Stale state is revalidated/recomputed before a consequential allow/block decision when deterministic.
5. `BLOCKED_DECISION` recommends clarification/decision rather than blind re-run of convergence.

### User Story 6 — Detect stale tasks after requirements repairs (Priority: P1)

If convergence changes relevant authoritative artifacts after `tasks.md` exists, tasks are reported stale.

**Acceptance Scenarios**:

1. `TASKS_STALE: true` is set when relevant upstream documentation changed after tasks.
2. Semantic convergence may report `CONVERGED_WITH_STALE_TASKS`.
3. Recommended next action is normal Spec Kit task regeneration/review.
4. `tasks.md` is never silently rewritten by checklist-converge.

### User Story 7 — Use the active agent's best safe tool surface (Priority: P1)

Different supported agents may use different native capabilities while preserving one semantic contract.

**Acceptance Scenarios**:

1. Lack of one particular named tool does not make the capability unsupported if an equivalent safe capability exists.
2. The skill does not attempt to invoke every available tool.
3. Any selected tool remains inside the effect/mutation/authority boundaries.
4. Parallel analysis is reconciled before controlled writes.

### User Story 8 — Bound convergence and detect no progress (Priority: P1)

PowerPack prevents repeated convergence loops.

**Acceptance Scenarios**:

1. Every pass records unresolved fingerprints/classifications.
2. Repeated equivalent unresolved state eventually returns `BLOCKED_NO_PROGRESS` according to plan-defined threshold.
3. Pass-budget exhaustion returns `BLOCKED_BUDGET`.
4. Clarification waiting does not repeatedly consume autonomous convergence passes.

### User Story 9 — Survive separate sessions and agent changes (Priority: P1)

State written in one session is usable in another supported agent session on the same checkout.

**Acceptance Scenarios**:

1. New consumer loads JSON and validates schema/revision/digests/fingerprints.
2. It does not depend on earlier ENV.
3. Artifact changes make the state `STALE` and require re-evaluation before consequential action.
4. Concurrent writes cannot silently overwrite a newer revision.

### User Story 10 — Support future visual workflow surfaces without requiring them (Priority: P2)

A future Canvas/UI can display checklist-converge as a quality gate while all semantics remain in PowerPack.

**Acceptance Scenarios**:

1. Machine-readable state exposes recommended action and command id.
2. A UI may render the gate between checklist and tasks.
3. UI actions invoke the registered PowerPack skill/command.
4. No Canvas/UI is required for normal operation.

## Checklist State Model

Conceptual persisted state:

```json
{
  "schema_version": 1,
  "state_type": "checklist-convergence",
  "spec": "003-checklist-converge",
  "revision": 12,
  "producer_run_id": "<run-id>",
  "validity": "FRESH",
  "semantic_status": "CONVERGENCE_REQUIRED",
  "source_artifacts": [
    {"path": "specs/.../spec.md", "digest": "sha256:..."},
    {"path": "specs/.../checklists/security.md", "digest": "sha256:..."}
  ],
  "checklists": [
    {
      "path": "checklists/security.md",
      "participation": "REQUIRED",
      "items": [
        {
          "id": "CHK007",
          "fingerprint": "sha256:...",
          "classification": "RESOLVABLE_GAP",
          "reason": "..."
        }
      ]
    }
  ],
  "tasks_stale": false,
  "recommended_action": "speckit.powerpack.checklist-converge",
  "updated_at": "<timestamp>"
}
```

## Functional Requirements

- **FR-001**: Expose native PowerPack command `speckit.powerpack.checklist-converge`.
- **FR-002**: Do not restore the removed legacy preset/runtime architecture or receipt prerequisite.
- **FR-003**: Resolve exactly one active SPEC and at least one applicable custom checklist or fail closed.
- **FR-004**: Exclude built-in upstream `checklists/requirements.md` from mutation by default.
- **FR-005**: Support direct explicit invocation without historical PowerPack completion receipts.
- **FR-006**: Use requirements/design artifacts, not application code/tests, to establish checklist satisfaction.
- **FR-007**: Apply the documented authority order consistently.
- **FR-008**: Assign exactly one allowed classification to each evaluated item.
- **FR-009**: Repair only deterministic documentation gaps supported by existing authority.
- **FR-010**: New product/security/UX/business/compliance/architecture/operations intent MUST yield blocking/clarification state.
- **FR-011**: Preserve checklist wording/format and update `[x]` only after explicit convergence evaluation justifies satisfaction.
- **FR-012**: Never modify application code/tests/build/deployment/remote systems.
- **FR-013**: Use `before_checklist`/`after_checklist` or equivalent deterministic run-delta capture when available.
- **FR-014**: `after_checklist` MUST be requirements-read-only and may persist only PowerPack state/reporting outputs.
- **FR-015**: Persist durable checklist state in project-local JSON with schema version, revision, source digests and item fingerprints.
- **FR-016**: Independent consumers MUST reload JSON and MUST NOT rely on ENV exported by a prior hook/session.
- **FR-017**: Separate `validity` from semantic checklist status.
- **FR-018**: Use atomic write plus conflict detection to prevent partial state and silent lost updates.
- **FR-019**: Support REQUIRED/ADVISORY/IGNORED participation semantics.
- **FR-020**: `before_tasks` MUST block only according to REQUIRED-gate policy and latest valid state.
- **FR-021**: Requirements changes after tasks exist MUST report `TASKS_STALE`; checklist-converge MUST NOT rewrite tasks automatically.
- **FR-022**: Clarification changes invalidate prior analysis and require re-evaluation.
- **FR-023**: The portable capability MUST NOT impose a fixed named-tool allowlist solely to mirror one agent integration.
- **FR-024**: Tool use MUST remain within the effect policy regardless of tool name/provider.
- **FR-025**: External evidence MAY support existing referenced standards/contracts but MUST NOT create missing user intent.
- **FR-026**: Safe parallel analysis MAY be used, but concurrent writes require reconciliation/serialization/conflict detection.
- **FR-027**: Convergence MUST have a bounded pass budget distinct from implement-review rounds.
- **FR-028**: Repeated no-progress state MUST terminate explicitly rather than loop indefinitely.
- **FR-029**: Machine-readable status MUST expose participation, validity, semantic status, classification counts, tasks stale state and recommended action.
- **FR-030**: Normal operation MUST NOT require Copilot Canvas or any UI adapter.
- **FR-031**: If shared PowerPack infrastructure from another accepted spec exists, implementation SHOULD reuse it while preserving this SPEC's independent user-visible contract.

## Success Criteria

- **SC-001**: A clean fixture can run checklist analysis and direct checklist-converge without any legacy receipt state.
- **SC-002**: Unchecked-only checklist fixtures produce zero false automatic `CONVERGENCE_REQUIRED` classifications solely because boxes are unchecked.
- **SC-003**: Deterministic documentation gaps can be repaired and re-evaluated with zero application-code/test mutations.
- **SC-004**: New-intent fixtures always block/clarify rather than synthesize authority.
- **SC-005**: REQUIRED/ADVISORY/IGNORED fixtures yield the expected task-gate behavior in 100% of contract tests.
- **SC-006**: State produced in one session is recovered in another after freshness validation without reliance on persistent ENV.
- **SC-007**: Concurrent-writer tests produce zero silent lost updates.
- **SC-008**: Stale item/content fingerprints are never reused as fresh evaluations.
- **SC-009**: No-progress/budget fixtures always terminate with explicit blocking state rather than infinite/redundant passes.
- **SC-010**: Codex and Claude Code homologation demonstrate equivalent semantic outcomes despite different native tool surfaces.
- **SC-011**: Machine-readable state contains enough information for a future UI adapter to render the checklist-converge gate without duplicating convergence business logic.

## Assumptions

- Current Spec Kit provides native checklist/tasks lifecycle hooks such as `before_checklist`, `after_checklist`, and `before_tasks` in the targeted compatibility range.
- Custom checklist files remain reviewer-owned requirements-quality artifacts.
- Agent integrations differ in available tools; semantic capability, not named-tool equality, is the portability target.
- Project-local mutable state can persist across sessions on the same checkout.
- A later accepted infrastructure spec may centralize state/doctor/setup services without changing this capability's externally visible semantics.

## Non-Goals

- Restoring all capabilities removed by SPEC-001.
- Treating implementation code/tests as checklist proof.
- Automatically inventing product/security/business decisions.
- Automatically rewriting `tasks.md` after requirement changes.
- Requiring every available agent tool to be invoked.
- Persisting workflow state through `.bashrc`, PowerShell profiles or global environment variables.
- Making a Copilot-specific Canvas the workflow authority or a runtime requirement.

## Core Invariants

```text
functional PowerPack capabilities == {
  implement-review,
  checklist-converge
}
```

```text
CHECKLIST_ITEM_SATISFACTION
  => authoritative_requirements_evidence
  != application_implementation_evidence
```

```text
MORE_AGENT_CAPABILITIES != MORE_DECISION_AUTHORITY
```

```text
tool_surface = agent_capability_driven
mutation_surface = requirements_documentation_only
```

```text
unchecked_item != requirements_gap
```

```text
PERSISTENT_CHECKLIST_STATE == project_local_json
independent_hook_or_session != rely_on_previous_ENV
```

```text
validity != semantic_status
```

```text
REQUIRED + unresolved_consequential_finding
  => before_tasks_block
```

```text
requirements_changed_after_tasks
  => TASKS_STALE == true
  => tasks_not_silently_rewritten
```

```text
convergence_budget_exhausted or no_progress
  => BLOCKED
  != CONVERGED
```

```text
UI_OR_CANVAS
  => adapter_over_authoritative_runtime
  != second_workflow_engine
```
