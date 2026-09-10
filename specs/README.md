# Specify PowerPack — Specification Registry and Workflow Gates

This directory contains the product specifications that evolve Specify PowerPack itself.

## Specification immutability rule

A specification that has entered implementation/review is treated as a historical contract. New behavior that changes that contract MUST be introduced by a successor SPEC instead of rewriting the earlier SPEC.

Current status:

| SPEC | Capability | Lifecycle |
|---|---|---|
| `001-single-skill-baseline` | Single-skill baseline / `implement-review` | **FROZEN — implementation in PR review** |
| `002-plugin-setup-routing` | Native bundle, setup, routing and persistent infrastructure | Draft |
| `003-checklist-converge` | Requirements-quality checklist convergence | Draft specification merged to `main` |
| `004-implementation-convergence-review-gates` | Implementation convergence, review repair lifecycle and artifact gates | Draft |

**SPEC-001 MUST NOT be modified by SPEC-004.** If the accepted implementation of SPEC-001 changes the runtime ownership of `speckit-implement`, `speckit-converge` or `implement-review`, SPEC-004 MUST adapt through a later PowerPack composition/runtime layer while preserving the accepted SPEC-001 history.

## Canonical user-driven workflow

The intended workflow is:

```text
speckit-specify <spec>
→ speckit-clarify <spec>
→ speckit-plan <spec>
→ speckit-checklist <spec>
→ speckit-checklist-converge <spec>
→ speckit-tasks <spec>
→ speckit-analyze <spec>
→ speckit-implement <spec>
→ speckit-converge <spec>
→ speckit-implement-review <spec>
```

`<spec>` is optional when the active SPEC can be resolved unambiguously from repository context such as `<repo-root>/.specify/feature.json`. Explicit arguments are user-controlled context overrides/focus, not a requirement for normal progression.

The post-implementation portion is intentionally repeatable:

```text
IMPLEMENT
   ↓
CONVERGE
   ├─ findings ─────────────→ user chooses whether to invoke IMPLEMENT again
   │
   └─ CONVERGED ────────────→ user chooses whether to invoke IMPLEMENT-REVIEW
                                      │
                                      ├─ APPROVED → done
                                      │
                                      └─ findings → user chooses whether to invoke IMPLEMENT
                                                         ↓
                                                     CONVERGE
                                                         ↓
                                                  IMPLEMENT-REVIEW
                                                         ↓
                                                        ...
```

The lifecycle may require any number of repair rounds, but **a command invocation authorizes only that command**. A command MAY persist state and recommend the next action; it MUST NOT invoke the next workflow phase unless the user has explicitly selected an orchestration mode that grants that authority.

## Command semantics

### `speckit-implement`

`implement` is the same command for initial delivery, convergence repair and review repair.

It resolves the active SPEC, authoritative Spec Kit artifacts and any currently actionable persisted findings. The user does not have to pass finding identifiers. Explicit parameters MAY narrow/focus context when the user chooses to do so.

`implement` MUST NOT require a prior convergence receipt in order to apply repair work.

### `speckit-converge`

`converge` is the same command after every implementation attempt.

It evaluates the latest implementation of the active SPEC against the authoritative Spec Kit artifacts and configured quality/convergence rules. Its algorithm MUST NOT branch into a special "review convergence" mode merely because the implementation was triggered by review findings.

Finding provenance MAY be retained for audit linkage, but provenance MUST NOT alter convergence semantics.

### `speckit-implement-review`

`implement-review` reviews only an implementation snapshot that has a current successful convergence attestation. Review findings are persisted as repair inputs for a later `speckit-implement`; they are not silently converted into `tasks.md` entries.

A later review round MUST explicitly account for unresolved findings from prior review rounds.

## Artifact gates

The workflow is controlled by persisted evidence, not by parsing optimistic human prose such as `✅ Convergência concluída`.

| Gate | Transition | Required evidence | Failure behavior |
|---|---|---|---|
| G0 | any SPEC-scoped command | exactly one resolvable active SPEC | fail closed; request explicit SPEC selection |
| G1 | checklist/checklist-converge → tasks | required checklist-convergence state is fresh and non-blocking when SPEC-003 policy applies | block `tasks`; recommend checklist convergence or clarification |
| G2 | implement → converge | current implementation evidence exists for the active SPEC | block `converge`; recommend `implement` |
| G3 | converge → implement-review | latest implementation has a fresh `CONVERGED` attestation bound to that implementation/snapshot | block review; recommend `converge` |
| G4 | review start | convergence evidence and review manifest identify the same current implementation snapshot | fail closed as stale/mismatched evidence |
| G5 | review round N+1 | prior review findings are carried forward and dispositioned | validation fails; review cannot approve |
| G6 | every phase boundary | user consent exists for the command being invoked | stop after current command and only recommend next action |

## Artifact classes

PowerPack MUST keep these classes distinct:

```text
SPEC KIT AUTHORITATIVE ARTIFACTS
  spec.md
  plan.md
  checklists/
  tasks.md
  other accepted Spec Kit design artifacts

POWERPACK WORKFLOW STATE
  active feature/SPEC resolution metadata
  implementation evidence
  convergence evidence
  persistent finding lifecycle/linkage

POWERPACK REVIEW EVIDENCE
  immutable review manifest
  review rounds
  prior-finding dispositions
  final verdict evidence
```

Review or convergence findings MUST NOT be appended to `tasks.md` automatically. `tasks.md` remains the planned task artifact of the SPEC; findings are emergent evidence/repair obligations with their own persisted identity.

## Freshness rule

A successful gate is valid only for the artifact/snapshot it evaluated. A relevant implementation or authoritative-artifact mutation after convergence makes that convergence evidence stale for review.

Conceptually:

```text
latest_implementation.id == convergence.implementation_id
AND
latest_implementation.snapshot == convergence.snapshot
AND
convergence.status == CONVERGED
```

Otherwise `implement-review` is blocked and the suggested next action is `speckit-converge`.

## Consent rule

Default workflow behavior is manual and user-driven:

```text
command executes
→ persists evidence/state
→ prints result
→ recommends next action
→ STOP
```

A future/full-cycle orchestration capability MAY execute multiple phases only after explicit user consent and MUST use bounded repair/no-progress budgets. That orchestration does not change the individual command contracts above.
