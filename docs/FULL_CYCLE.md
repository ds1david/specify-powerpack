# Full cycle

The PowerPack full-cycle orchestrator composes official Spec Kit stages; it does not redefine Spec Kit.

```text
clarify
→ plan
→ checklist
→ checklist-converge
→ tasks
→ analyze
→ implement
→ implement-review
→ DONE
```

## Same-SPEC safety

Receipts are scoped to one SPEC. Artifacts merely existing on disk do not prove that a predecessor ran for the active SPEC.

The initial `speckit-implement` is explicit. `speckit-implement-review` cannot manufacture this predecessor.

## What implement-review owns

After the initial implementation, implement-review owns its internal convergence loop:

```text
converge
  → appended deterministic tasks? implement those tasks → converge
  → clean? capability quality gate
  → browserless deep PR review
  → findings? implement → converge → quality gate → fresh review
```

Any implementation change invalidates the previous review snapshot.

## Budgets

Convergence/review budgets are explicit and never silently extended. When configured budget is exhausted, the workflow returns a blocked budget state and requires an explicit extension/owner decision.

## Quality gates

PowerPack does not hard-code Maven, Gradle, npm, pytest or another project-specific command. `.specify/powerpack/bin/capabilities.py` resolves a deterministic project strategy. Unknown or ambiguous architectures fail closed unless the project supplies an explicit custom gate.

## Review provider

The supported independent PR provider uses:

- Codex authentication;
- serialized ChatGPT Project context;
- GitHub Codex App/MCP evidence;
- immutable PR manifests;
- Deep Review Protocol schema 2.0.

See [`IMPLEMENT_REVIEW.md`](IMPLEMENT_REVIEW.md).

## Technical debt

Current SPEC gaps, active review findings and blockers cannot be moved to debt to obtain `DONE`. See [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md).
