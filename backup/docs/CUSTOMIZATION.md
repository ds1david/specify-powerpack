# Customization

**Specify PowerPack** is intended to be reused across projects with different languages, frameworks and build systems. Customize policy and capability inputs, not generated provider internals.

## Project nature and evolution

Specify PowerPack is a personal project in continuous evolution. Its behavior reflects workflow, quality, safety, portability and developer-experience criteria proven useful through hands-on use, while the project is progressively generalized into an effective reusable plugin for projects from different domains, architectures, languages, frameworks and delivery contexts.

That evolution has two different forms and they must not be confused:

- **corrections** to behavior already promised by the active SPEC, documentation, contracts or non-weakenable invariants;
- **new capabilities** that deliberately broaden what Specify PowerPack can support, automate, discover, integrate or customize.

Continuous evolution is expected. The absence of a capability that has never been part of the current contract is not automatically a defect.

## Bug versus new capability

Reviews, issues and maintenance work MUST distinguish an actual defect from a request to expand the product.

Treat something as a **bug/defect** when there is evidence that the current implementation:

- violates an active SPEC requirement or acceptance criterion;
- contradicts documented behavior or an explicit public/internal contract;
- breaks a non-weakenable Specify PowerPack invariant;
- regresses behavior that the current baseline is expected to preserve;
- produces incorrect, unsafe or inconsistent behavior within a capability the project already claims to support.

Treat something as a **new capability/enhancement** when it primarily asks Specify PowerPack to:

- support a provider, platform, workflow, architecture or integration not currently promised;
- automate an additional step that is manual by design;
- generalize an existing mechanism beyond its documented scope;
- add optional UX, observability, discovery or convenience behavior;
- adopt a new product or architectural requirement that has not yet been promoted into the active SPEC or durable project policy.

A capability request becomes current-scope implementation work only after it is deliberately accepted into the relevant SPEC, plan, policy or contract. Once accepted, failure to implement it correctly can become a defect or SPEC non-compliance.

This distinction matters especially for AI-assisted review. A reviewer must not block a valid implementation merely because it can imagine a broader product. A blocking finding requires concrete evidence of failure against the **current** contract. Ideas that extend the contract belong in capability planning.

## Safe project customization

Versionable configuration lives under `.specify/powerpack/`, including:

- `model-routing.json`
- `quality-gates.json`
- `full-cycle.json`
- `technical-debt.json`
- `review.json`
- project policy/docs added by the consuming repository

Project-specific quality commands should be expressed through capability/custom-gate configuration rather than editing packaged Python runtime files.

## Review configuration

`review.json` schema 5 represents the supported provider:

```json
{
  "provider": "chatgpt-project",
  "review_backend": "codex-apps-github",
  "mode": "browserless",
  "deep_review": {
    "immutable_pr_manifest": true,
    "exact_changed_file_coverage": true,
    "exact_requirement_coverage": true,
    "inspection_evidence_required": true,
    "context_gaps_block_approval": true
  },
  "chatgpt_project": {
    "authorization": "codex-backend-api",
    "context_mode": "serialized",
    "native_binding": false
  },
  "github_app": {
    "runtime": "codex_apps",
    "explicit_app_mention": true,
    "require_structural_tool_evidence": true,
    "allow_shell_fallback": false,
    "allow_web_search_fallback": false
  }
}
```

Project identity fields are normally written by `specify-powerpack review setup`; do not hand-copy Project IDs when interactive discovery is available.

## Non-customizable safety floor

Projects may make gates stricter, but should not weaken these invariants:

- exact PR required for PR review;
- one resolved active SPEC;
- local HEAD must equal PR head;
- GitHub tool evidence required;
- shell/web-search fallback forbidden for GitHub evidence;
- Project context is background, not authoritative code evidence;
- exact changed-file and requirement coverage where applicable;
- concrete inspection evidence for every changed file;
- adversarial verdict challenge required;
- Project-only context gaps block approval until made durable;
- Deep Review Protocol validation required;
- active findings cannot be escaped to technical debt;
- review runs are read-only and do not merge/approve PRs.

## Managed files

`install` and `update` refresh packaged runtime/preset/extension assets. Mutable config is preserved unless `--reset-config` is explicitly supplied.

Avoid editing files under `.specify/powerpack/bin/` because they are managed copies. Contribute reusable runtime changes to the Specify PowerPack source package instead.
