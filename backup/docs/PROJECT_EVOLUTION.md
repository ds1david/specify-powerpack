# Project evolution and review scope

Specify PowerPack is a **personal project in continuous evolution**. Its current direction reflects workflow, quality, safety, portability and developer-experience criteria that I consider useful and necessary based on practical use and ongoing learning.

The project is intentionally being generalized over time. The long-term goal is to mature Specify PowerPack into an effective, reusable plugin that can be applied to projects from different business domains, architectures, languages, frameworks and delivery contexts without requiring a fork of the PowerPack itself.

This evolution is part of the product strategy, not evidence that the current implementation is defective. Reviews and maintenance work must therefore distinguish failures against the current contract from proposals that expand that contract.

## Bug / defect

Treat an item as a bug or defect when there is concrete evidence that the current implementation:

- violates an active SPEC requirement or acceptance criterion;
- contradicts documented behavior or an explicit contract;
- breaks a non-weakenable Specify PowerPack invariant;
- regresses behavior the current baseline is expected to preserve;
- behaves incorrectly, unsafely or inconsistently inside a capability the project already claims to support.

A defect is current-scope corrective work and may be a blocking review finding.

## New capability / enhancement

Treat an item as a new capability or enhancement when it primarily asks Specify PowerPack to:

- support a new platform, provider, workflow, architecture or integration not currently promised;
- automate an additional step that is currently manual or intentionally outside the supported flow;
- generalize an existing mechanism beyond its documented scope;
- introduce additional UX, observability, discovery, convenience or configurability;
- adopt a newly identified product, architectural or operational requirement that has not yet been promoted into an active SPEC or durable project policy.

A useful idea is not automatically a defect. Capability proposals belong in specification and product evolution until they are deliberately accepted into the current contract.

## When a capability becomes current-scope work

A new capability becomes part of the current implementation obligation only after it is explicitly accepted into a durable source of truth, for example:

- an active `spec.md` requirement;
- acceptance criteria or success criteria;
- `plan.md` / `tasks.md` for the active SPEC;
- architecture documentation or ADR;
- project constitution or non-weakenable policy;
- an explicit supported-capability contract.

Once accepted, failure to implement or preserve that capability can legitimately be classified as SPEC non-compliance, regression or defect.

## Rule for AI-assisted review

AI reviewers must review the implementation that was actually specified, not the broader product they can imagine.

A blocking finding requires evidence of failure against the **current contract**. Reviewers may identify potentially valuable future capabilities, but those ideas must not be converted into blocking findings unless they expose a concrete violation of an existing requirement, contract, invariant or preserved behavior.

This rule protects convergence while still allowing the project to evolve aggressively. Product evolution remains encouraged; defect classification remains evidence-bound.

## Practical decision rule

```text
Does the current SPEC, contract, invariant or preserved baseline require it?
                         |
                   +-----+-----+
                   |           |
                  yes          no
                   |           |
         Is current behavior   New capability /
          incorrect or absent? enhancement proposal
                   |
                  yes
                   |
              bug / defect
```

When the answer changes because a capability has been deliberately added to the active contract, the classification can change as well.
