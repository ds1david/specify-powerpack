---
description: "Check/update SpecKit PowerPack and rematerialize project-managed assets without destructive Git operations."
---

# SpecKit PowerPack Update

This command manages the installed PowerPack CLI and its managed project assets.

## Check current source

```bash
speckit-powerpack update . --check
```

The result reports the effective VCS source/ref and installed/remote commit when they can be resolved. Explicit commit-SHA installations remain pinned; PowerPack does not silently reinterpret a pinned build as `main`.

## Normal update

```bash
speckit-powerpack update .
```

A normal update:

1. reinstalls the `speckit-powerpack` CLI through `uv` from the effective Git source/ref;
2. rematerializes PowerPack-managed runtime/preset/extension assets in the current repository;
3. preserves mutable PowerPack project configuration by default;
4. performs no destructive Git operation on application/source history.

## Project-only refresh

When the installed CLI is already correct and only managed project assets need refresh:

```bash
speckit-powerpack update . --project-only
```

This is the preferred recovery path for missing/corrupted `.specify/powerpack/bin/*`, presets or extensions when the CLI itself does not need reinstalling.

## Bootstrap/upgrade Spec Kit while refreshing

```bash
speckit-powerpack update . --project-only --bootstrap-speckit
```

Use this when the project needs the tested compatible official Spec Kit release as part of rematerialization.

## Explicit source/ref override

```bash
speckit-powerpack update . \
  --repository https://github.com/ds1david/speckit-powerpack.git \
  --ref <branch-tag-or-commit>
```

A feature-branch or immutable-SHA install therefore remains explicit and reproducible.

## Configuration reset

Resetting mutable PowerPack configuration is a separate, explicit operation:

```bash
speckit-powerpack update . --project-only --reset-config
```

This may recreate `review.json`, model routing, full-cycle, technical-debt and other packaged defaults. It can remove the current ChatGPT Project binding, so `speckit-powerpack review setup --path .` may be required afterward.

Never add `--reset-config` merely to fix a managed runtime file.

## Safety boundary

Update/rematerialization does not authorize:

- Git reset/rebase/clean;
- force-push;
- source-code deletion;
- GitHub PR mutation;
- deletion/copying of Codex/ChatGPT credentials.

The browserless reviewer keeps authentication in the user's Codex auth store; there are no PowerPack-managed browser profiles to preserve or migrate.
