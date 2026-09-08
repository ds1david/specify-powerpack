# Customization

**Specify PowerPack** is intended to be reused across projects with different languages, frameworks and build systems. Customize policy and capability inputs, not generated provider internals.

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
- Deep Review Protocol validation required;
- active findings cannot be escaped to technical debt;
- review runs are read-only and do not merge/approve PRs.

## Managed files

`install` and `update` refresh packaged runtime/preset/extension assets. Mutable config is preserved unless `--reset-config` is explicitly supplied.

Avoid editing files under `.specify/powerpack/bin/` because they are managed copies. Contribute reusable runtime changes to the Specify PowerPack source package instead.
