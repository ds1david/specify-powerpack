---
description: "Check/update Specify PowerPack and rematerialize project-managed assets without destructive Git operations."
---

# Specify PowerPack Update

This command manages the installed Specify PowerPack CLI and its managed project assets.

## Check current source

```bash
specify-powerpack update . --check
```

The result reports the effective VCS source/ref and installed/remote commit when they can be resolved. Explicit commit-SHA installations remain pinned; Specify PowerPack does not silently reinterpret a pinned build as `main`.

## Normal update

```bash
specify-powerpack update .
```

A normal update:

1. reinstalls the `specify-powerpack` CLI through `uv` from the effective Git source/ref;
2. rematerializes Specify PowerPack-managed runtime/preset/extension assets in the current repository;
3. preserves mutable PowerPack project configuration by default;
4. performs no destructive Git operation on application/source history.

## Project-only refresh

When the installed CLI is already correct and only managed project assets need refresh:

```bash
specify-powerpack update . --project-only
```

This is the preferred recovery path for missing/corrupted `.specify/powerpack/bin/*`, presets or extensions when the CLI itself does not need reinstalling.

## Bootstrap/upgrade Spec Kit while refreshing

```bash
specify-powerpack update . --project-only --bootstrap-speckit
```

Use this when the project needs the tested compatible official Spec Kit release as part of rematerialization.

## Explicit source/ref override

```bash
specify-powerpack update . \
  --repository https://github.com/ds1david/specify-powerpack.git \
  --ref <branch-tag-or-commit>
```

A feature-branch or immutable-SHA install therefore remains explicit and reproducible.

## Configuration reset

Resetting mutable PowerPack configuration is a separate, explicit operation:

```bash
specify-powerpack update . --project-only --reset-config
```

This may recreate `review.json`, `model-routing.json`, `prerequisites.json` and other packaged defaults. It can remove the current ChatGPT Project binding, so `specify-powerpack review setup --path .` may be required afterward.

Never add `--reset-config` merely to fix a managed runtime file.

## Compatibility

The legacy `speckit-powerpack` command remains a compatibility alias. New automation and documentation should use `specify-powerpack`.

## Safety boundary

Update/rematerialization does not authorize:

- Git reset/rebase/clean;
- force-push;
- source-code deletion;
- GitHub PR mutation;
- deletion/copying of Codex/ChatGPT credentials.

The browserless reviewer keeps authentication in the user's Codex auth store; no browser automation state is part of Specify PowerPack readiness or migration.
