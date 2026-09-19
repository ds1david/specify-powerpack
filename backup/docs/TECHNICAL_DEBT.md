# Technical debt governance

PowerPack treats technical debt as an explicit governed lifecycle, not as an escape hatch from current implementation or review work.

## Hard boundary

The following cannot be converted to debt merely to finish the current workflow:

- unmet active SPEC requirements;
- deterministic convergence work;
- active Deep Review findings;
- blockers that prevent responsible approval;
- regressions introduced by the current implementation.

Those items remain current-flow work until resolved or the owning product/specification stage makes an explicit scope decision.

## Lifecycle

The packaged debt runtime supports the explicit lifecycle represented by the debt commands (`create`, `list`, `consult`, `start`, `close`). The default ledger is Markdown and uses the packaged template/policy.

Debt records should state the decision, rationale, impact, evidence, owner/status and the condition for revisiting/closing the item.

## Review interaction

A code-review finding remains a review finding. Implement-review persists/fixes it and reruns convergence plus review against a fresh immutable snapshot.

Moving a finding to `docs/technical-debt.md`, a TODO or backlog does not satisfy Deep Review Protocol resolution.

## Customization

Projects may add stricter debt rules. They should not weaken the PowerPack floor that forbids active review findings, convergence gaps and blockers from becoming debt escape hatches.
