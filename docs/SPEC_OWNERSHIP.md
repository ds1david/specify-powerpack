# Specification Ownership and Responsibility Boundaries

Specify PowerPack specifications are capability contracts, not a single accumulating requirements document.

A later specification may reuse infrastructure from an earlier specification without becoming co-owner of another capability's semantics.

## Ownership model

```text
CAPABILITY OWNER
    owns WHAT the capability means

INFRASTRUCTURE OWNER
    owns generic mechanisms used by capabilities

ORCHESTRATOR
    owns WHEN capabilities are invoked
```

A functional capability MUST have exactly one normative owner specification or explicit amendment chain.

A later specification that intentionally changes an existing capability's states, transitions, gates, evidence semantics, provider behavior, budgets, failure semantics or approval semantics MUST explicitly declare itself an amendment to that capability owner.

## Current map

| Specification | Responsibility |
|---|---|
| SPEC-001 — Single Skill Baseline | Baseline product surface; initial preservation of `implement-review`; removal of legacy PowerPack commands; implementation predecessor evidence |
| SPEC-001A — Review Lineage, GPT Web Continuity and Reproducibility (physical SPEC-004) | Complete `implement-review` review semantics: identity, snapshots, rounds, attempts, GPT Web conversation segments, review protocol, finding lifecycle, reconciliation, divergence and approval |
| SPEC-002 — Plugin Setup/Routing | Generic PowerPack plugin infrastructure: native composition, extension/presets, capability registry, setup/configuration, generic persistent state, component coherence, diagnostics/doctor |
| SPEC-003 — Checklist Convergence | Complete `checklist-converge` semantics |
| Future orchestration specs | Stage ordering and handoff between capability contracts; no redefinition of capability internals without amendment declaration |

## SPEC-001 / SPEC-001A

SPEC-001 is intentionally historical and must not be rewritten to retroactively incorporate post-implementation review redesigns.

SPEC-001A is the amendment chain for the independent review subsystem introduced/preserved by SPEC-001.

When SPEC-001A and transport/continuity details in SPEC-001 differ, SPEC-001A controls only the independent review subsystem. Unrelated SPEC-001 baseline requirements remain intact.

## SPEC-002 boundary

SPEC-002 may discover and expose environment facts used by capabilities, for example:

```text
integration installed
authentication ready
connector available
component set coherent
```

The capability owner decides what those facts mean for capability readiness and behavior.

For `implement-review`, SPEC-001A owns that interpretation.

SPEC-002 review-specific draft clauses do not become a competing `implement-review` contract. In particular, SPEC-001A owns the semantics previously described by SPEC-002 FR-021..FR-024 and FR-032..FR-036.

## SPEC-003 boundary

SPEC-003 owns checklist-specific state and behavior. Generic persistence mechanisms should converge on SPEC-002 shared infrastructure when available.

The following remain checklist-specific:

- item classifications;
- REQUIRED / ADVISORY / IGNORED participation;
- checklist/task hook behavior;
- clarification requirements;
- task-staleness semantics;
- checklist convergence/no-progress budget;
- checklist-specific persisted fields.

`checklist-converge` budget and `implement-review` review budget are independent.

## Amendment declaration

A future specification that changes an existing capability should state:

```text
Amends: <owner specification>
Affected capability: <capability id>
Superseded clauses: <explicit list>
Preserved clauses: <explicit scope>
```

Without that declaration, infrastructure and orchestration specifications consume existing capability contracts rather than redefine them.
