# Updates and recovery

PowerPack separates CLI installation from project materialization.

## Check

```bash
speckit-powerpack update . --check
```

For Git/VCS installs, PowerPack reads PEP 610 `direct_url.json` metadata to identify repository, requested revision and installed commit.

An explicit commit-SHA installation is considered pinned and is not silently reinterpreted as `main`.

## Update CLI and project assets

```bash
speckit-powerpack update .
```

The CLI is reinstalled using `uv tool install --force` from the effective repository/ref, then PowerPack assets are rematerialized in the project.

## Project-only refresh

```bash
speckit-powerpack update . --project-only
```

This does not reinstall the CLI.

## Change source/ref explicitly

```bash
speckit-powerpack update . \
  --repository https://github.com/ds1david/speckit-powerpack.git \
  --ref main
```

## Configuration preservation

Managed runtime/preset/extension files are refreshed. Mutable project configuration is preserved by default.

The review-config migration converts supported legacy Project identity into schema 5 and intentionally drops obsolete browser/Web2API fields.

To intentionally reset mutable PowerPack config:

```bash
speckit-powerpack update . --project-only --reset-config
```

This can remove the current ChatGPT Project binding, so `review setup` may be required again.

## Safety boundary

PowerPack update does not authorize destructive Git reset/rebase/force-push, source deletion or GitHub mutations. It only updates its CLI and owned project assets/configuration according to the requested flags.

## Recovery

For an existing Spec Kit project with damaged/missing PowerPack managed assets:

```bash
speckit-powerpack install . --integration codex --bootstrap-speckit
```

If configuration itself should also be recreated, add `--reset-config` deliberately.

For a machine with no working PowerPack CLI, rerun the repository bootstrap described in [`INSTALLATION.md`](INSTALLATION.md).
