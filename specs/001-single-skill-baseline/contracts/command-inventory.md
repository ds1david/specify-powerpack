# Contract: `powerpack-core` Command Inventory

**Purpose.** Define the one canonical way the PowerPack command set is enumerated, so
FR-004 / FR-011 equality assertions have a single source of truth.

## Registration-time enumeration

**Source of truth:** `src/speckit_powerpack/assets/presets/powerpack-core/preset.yml`,
the `provides.templates` list.

**Rule:** the command set = `{ entry.name for entry in preset.provides.templates
if entry.type == "command" }`.

**Assertion (contract test):**

```
registered = parse_preset_command_names("assets/presets/powerpack-core/preset.yml")
assert registered == {"speckit.implement-review"}      # equality, not "in"
```

Also assert structural consistency:
- exactly one `commands/*.md` file exists under the preset, named `speckit.implement-review.md`;
- `preset.yml` contains no `file:` reference to any other `commands/*.md`;
- no `speckit.implement-review-v2.md` (guard against accidental fork — existing check kept).

Parsing may use any stdlib approach in tests. Shipped code must not add a YAML dependency
(runtime is stdlib-only); `preset.yml` command entries are flat `key: "value"` lines and
scan cleanly with a small regex if shipped code ever needs them.

## Install-time enumeration

**Source of truth:** the command files Spec Kit materializes for the active integration
after `install_components()` runs `specify preset add` — i.e. the integration's command
directory (e.g. `.codex/commands/` or `.claude/commands/` under the target project),
filtered to PowerPack-provided names.

**Rule:** `installed = { basename without extension, for command files whose provenance is
the powerpack-core preset }`. If provenance is not directly attributable, re-derive from the
installed preset registration copy.

**Assertion (contract test, clean temp project):**

```
project = tmp_path
install_powerpack(project, integration="codex", initialize=True, bootstrap=...)
installed = enumerate_powerpack_core_commands(project)
assert installed == {"speckit.implement-review"}
assert no_removed_command_assets_under(project / ".specify" / "powerpack")
```

`no_removed_command_assets_under` checks the absence of: `bin/debt.py`,
`bin/full_cycle.py`, `technical-debt-policy.md`, `technical-debt-template.md`,
`technical-debt.json`, `full-cycle.json`, and any `commands/speckit.debt-*`,
`speckit.full-cycle`, `speckit.implement.md`, `speckit.converge.md`,
`speckit.checklist-converge.md`.

## Surface boundary

"Single skill" in SPEC-001 means exactly one **PowerPack-owned command** in the
`powerpack-core` preset. It does not mean deleting or renaming upstream Spec Kit skills
such as `speckit-plan`, `speckit-implement`, or `speckit-converge`; those are predecessor
capabilities consumed by `implement-review`, not PowerPack registrations. The separate
`powerpack-tools` extension is also an explicitly preserved infrastructure surface.
Tests enumerate the PowerPack preset registration and materialized PowerPack command
namespace, while checking that removed PowerPack names are neither materialized nor
redirected. They do not count upstream skills as PowerPack commands.

## Out of scope for these assertions

- `powerpack-tools` extension commands `speckit.powerpack-tools.doctor` /
  `speckit.powerpack-tools.update` (preserved infrastructure).
- Upstream Spec Kit skills / commands (`speckit-plan`, `speckit-implement`,
  `speckit-converge`, …) under the host project's `.claude/skills/`.

## Negative behavior (FR-014 / FR-015)

Invoking a removed command name against a clean install behaves as an unknown command — no
silent redirect to `implement-review`. Per FR-014 this MUST be checked **behaviourally**
(assert the name is unresolved at the registration/dispatch layer), not only by asserting
textual absence from source. Realized as a case in `tests/test_baseline_contract.py` (or the
smoke), task T035 — distinct from the textual residual scan (T034 / FR-016).
