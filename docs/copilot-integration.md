# GitHub Copilot integration for Specify PowerPack

This guide explains how Copilot fits into this repository without becoming the PowerPack runtime authority.

## Goals

The repository uses Copilot-specific configuration for three purposes:

1. give Copilot durable project/PowerPack instructions;
2. make generated Spec Kit/PowerPack skills discoverable in Copilot skills mode;
3. constrain Copilot CLI permissions during development and homologation without hard-coding the portable PowerPack skill runtime to a fixed tool list.

Copilot-specific configuration is an adapter layer. PowerPack behavior must remain portable to other supported Spec Kit integrations.

## Repository instruction layers

```text
AGENTS.md
    -> cross-agent repository guidance

.github/copilot-instructions.md
    -> Copilot repository-wide policy

.github/instructions/*.instructions.md
    -> Copilot path-specific policy

.github/skills/speckit-*/SKILL.md
    -> generated Spec Kit/Copilot skills
```

Repository and path-specific instructions guide Copilot behavior, but they are not a permission/security boundary. Copilot CLI permission flags are the enforcement layer for local CLI sessions.

## Current integration state

Do not assume the state from directory names. Check:

```bash
specify integration status
```

or inspect `.specify/integration.json`.

At the time this guide is introduced, `main` records Claude as the installed/default Spec Kit integration. Copilot must be added through the native Spec Kit lifecycle rather than by manually editing `.specify/integration.json`.

## Install Copilot as an additional integration

Keep the existing default integration and install Copilot explicitly in skills mode:

```bash
specify integration install copilot --integration-options="--skills"
specify integration status
```

Installing an additional integration does **not** change `default_integration`.

Skills mode is the preferred layout for this project:

```text
.github/skills/
    speckit-<command>/
        SKILL.md
```

The legacy/compatibility commands layout (`.github/agents/*.agent.md` plus `.github/prompts/*.prompt.md`) should only be used for an explicit compatibility test.

## Important: installed Copilot is not the same as PowerPack materialized for Copilot

Spec Kit registers extension and preset commands for the active/default integration. Therefore this sequence:

```text
Claude default
    -> install Copilot as secondary
```

does not prove that the current PowerPack extension/preset command set has been rendered into `.github/skills/`.

To homologate PowerPack skills on Copilot, activate Copilot through the native lifecycle:

```bash
specify integration use copilot
specify integration status
specify extension list
specify preset list
```

This activation step rescaffolds enabled extensions and presets for Copilot.

After Copilot homologation, restore the desired default explicitly, for example:

```bash
specify integration use claude
```

Do not silently switch the default integration from a PowerPack skill or setup flow.

### Refresh rule

If an extension/preset is updated while Copilot is non-default, do not assume Copilot's previously generated PowerPack skills are current. Activate Copilot again (or follow the relevant native upgrade/use lifecycle) before validating its generated skill set.

## PowerPack skill ownership

The generated Copilot skill is not the authoritative source of the PowerPack behavior:

```text
PowerPack extension/preset source
      -> Spec Kit registration/rendering
      -> .github/skills/speckit-powerpack-*/SKILL.md
      -> Copilot agent
```

For changes to a PowerPack skill:

1. change the extension/preset/template source;
2. validate its portable semantic contract;
3. activate/rescaffold Copilot;
4. inspect the generated Copilot skill;
5. homologate behavior with Copilot's actual tool surface.

Do not customize generated `.github/skills/speckit-*` files by hand as the normal implementation path.

## Copilot CLI permission model

Spec Kit's programmatic Copilot dispatch may run the Copilot CLI with broad permissions. For PowerPack development/homologation, use the repository launcher instead of relying on unrestricted dispatch:

```bash
python scripts/copilot-policy.py show
```

Two initial profiles exist.

### `observe`

Intended for read/review/diagnostic work.

```bash
python scripts/copilot-policy.py copilot --profile observe
```

It denies file write tools and selected high-impact remote shell actions.

For a Spec Kit command that may dispatch Copilot:

```bash
python scripts/copilot-policy.py speckit --profile observe -- integration status
```

### `author`

Intended for implementation or deterministic documentation repair.

```bash
python scripts/copilot-policy.py copilot --profile author
```

Writes are still available, but the launcher does not grant allow-all permissions. Copilot's normal approval model remains in effect. Selected high-impact remote shell actions are denied.

For Spec Kit-dispatched Copilot:

```bash
python scripts/copilot-policy.py speckit --profile author -- <specify arguments>
```

The launcher sets process-local:

```text
SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0
```

and supplies the profile's deny rules through:

```text
SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS
```

It does not modify `.bashrc`, PowerShell profiles, Windows global environment, or any persistent host configuration.

## Why we do not use `--available-tools` by default

PowerPack's portable skill design is capability-driven:

```text
available tools
    = tools exposed by the active agent
      ∩ tools allowed by the current environment
      ∩ tools appropriate for the operation
```

A fixed Copilot tool inventory would make Copilot-specific assumptions leak into portable PowerPack semantics. The repository policy therefore leaves the model's native tool surface visible and constrains **permission/effect** instead.

For a dedicated experiment, `--available-tools`/`--excluded-tools` may still be useful, but that should be an explicit Copilot-specific homologation scenario rather than a PowerPack portability requirement.

## Suggested capability profiles

These are semantic targets, not fixed tool-name allowlists.

| PowerPack activity | Copilot profile | Mutation expectation |
| --- | --- | --- |
| `doctor` / state inspection | `observe` | read-only |
| checklist post-hook analyzer | `observe` | only PowerPack state write should be performed by the trusted runtime, not arbitrary agent edits |
| `checklist-converge` | `author` | requirements/design documentation only; no application/test writes |
| review-only gate | `observe` | read-only |
| implementation/fix phase | `author` | repository writes allowed by the accepted implementation contract |
| release/publish/remote mutation | neither by default | explicit user action and dedicated policy required |

The PowerPack runtime may later enforce capability-specific effects more precisely; these profiles are repository development/homologation defaults, not the final runtime policy engine.

## Copilot App / VS Code / Canvas

The Python launcher controls **Copilot CLI** and Spec Kit processes that spawn Copilot CLI. It does not configure GitHub Copilot App, VS Code sandboxing, cloud-agent permissions, organization policies, or account-level settings.

Repository instructions still apply where the Copilot surface supports them, but platform permission/sandbox settings remain separate controls.

### Canvas

The upstream Spec Kit SDD Canvas is a Copilot-specific side-panel UI. It scans Spec Kit artifacts and invokes an explicit set of core `speckit-*` skills. Installing a PowerPack extension does not automatically add a new PowerPack stage to that Canvas.

A future PowerPack Canvas adapter should follow:

```text
PowerPack machine-readable state
        -> Canvas read model
        -> render PowerPack gate/status
        -> invoke generated PowerPack skill
        -> authoritative PowerPack runtime performs work
```

The Canvas must not implement checklist convergence, review routing, or state transitions independently.

## Homologation checklist for a new PowerPack skill on Copilot

1. `specify integration status` confirms Copilot is installed.
2. Activate Copilot with `specify integration use copilot` before testing extension/preset registration.
3. Confirm skills mode and inspect `.github/skills/`.
4. Confirm the expected PowerPack skill exists after native registration.
5. Verify repository/path-specific Copilot instructions are discovered.
6. Run an `observe` scenario and confirm prohibited writes fail.
7. Run an `author` scenario and confirm allowed writes remain approval-gated rather than globally allowed.
8. Confirm the skill uses Copilot-native capabilities without requiring a PowerPack fixed tool-name allowlist.
9. Confirm semantic mutation boundaries for the specific capability.
10. Restore the desired Spec Kit default integration explicitly after homologation.
