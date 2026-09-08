---
description: "Diagnose a SpecKit PowerPack installation and browserless review readiness."
---

# SpecKit PowerPack Doctor

Run normal installation diagnostics:

```bash
speckit-powerpack doctor .
```

Treat the CLI result as authoritative. Normal diagnostics validate the installation floor, including:

1. official Spec Kit CLI is available;
2. the repository is a Spec Kit project (`.specify/` exists);
3. PowerPack managed runtime is materialized;
4. the configured primary executor is available;
5. Codex CLI/auth and Project binding state are reported separately from hard installation failures.

For the mandatory browserless PR-review readiness gate run:

```bash
speckit-powerpack doctor . --strict-review
```

Strict review additionally requires:

- Codex CLI on `PATH`;
- valid Codex account authentication (`codex login`);
- repository bound to one ChatGPT Project with `authorization = codex-backend-api`;
- a live GitHub App/connector discovered for the authenticated account.

Inspect detailed live state with:

```bash
speckit-powerpack review status --path . --live
```

If no Project is bound, configure it with:

```bash
speckit-powerpack review setup --path .
```

or select explicitly:

```bash
speckit-powerpack review setup \
  --path . \
  --project '<project-id-or-unique-name-or-url>'
```

The supported reviewer transport is browserless Codex Apps MCP. No browser-automation component is part of review readiness.

No password, MFA code, bearer token, raw cookie or connector secret may be written into version-controlled project state.
