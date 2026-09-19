# PowerPack installation and usage

This is the supported operator path for installing and using Specify PowerPack in an existing Spec Kit project.

## Prerequisites

- Spec Kit `specify >= 1.0.0`.
- An initialized project with `.specify/init-options.json` and an active integration.
- Git with a `github.com` `origin`.
- Codex CLI authenticated with `codex login`.
- Exactly one enabled and available GitHub App/connector for independent review.

PowerPack supports the same script choice selected by `specify init`: `sh`, `ps` or `py`.

## Standard installation from a versioned release

Use a vetted, immutable PowerPack release. The examples below use `v0.4.0`.

### 1. Install the PowerPack extension

```bash
specify extension add powerpack --from \
  https://github.com/ds1david/specify-powerpack/releases/download/v0.4.0/specify-powerpack-extension-v0.4.0.zip
```

Spec Kit will show the normal **Untrusted Source** confirmation because a direct `--from` URL bypasses install-allowed extension catalogs. Review the repository/release, then confirm only if you trust the source.

The extension registers:

- `speckit.powerpack.deliver`
- `speckit.powerpack.doctor`

### 2. Register the versioned PowerPack step catalog

Current Spec Kit installs third-party workflow steps through a step catalog. Register the catalog from the same immutable release tag:

```bash
specify workflow step catalog add \
  https://raw.githubusercontent.com/ds1david/specify-powerpack/v0.4.0/catalogs/step-catalog.json \
  --name powerpack \
  --install-allowed
```

This is a PowerPack-owned curated catalog and contains only the `powerpack-control` step for this release.

### 3. Install the PowerPack control step

```bash
specify workflow step add powerpack-control
```

### 4. Install the delivery workflow

```bash
specify workflow add powerpack-delivery --from \
  https://github.com/ds1david/specify-powerpack/releases/download/v0.4.0/specify-powerpack-workflow-v0.4.0.zip
```

### 5. Validate the installation

Invoke the doctor through the active integration.

Logical command:

```text
speckit.powerpack.doctor
```

For Codex skills mode the materialized command normally uses the `$` skill prefix and a hyphenated skill name:

```text
$speckit-powerpack-doctor
```

A healthy installation exits zero and ends with `HEALTHY`.

## Use the delivery workflow

For a new feature:

```text
speckit.powerpack.deliver Implement ...
```

For an existing feature:

```text
speckit.powerpack.deliver spec-soak-003
```

Codex skills mode normally materializes that as:

```text
$speckit-powerpack-deliver spec-soak-003
```

PowerPack preserves valid work already completed manually, converges reviewer-owned checklists, re-runs analyze as a freshness pass, validates `plan.md` + `tasks.md`, executes implementation through `speckit.implement`, runs `speckit.converge` until stable, prepares the exact PR/HEAD and enters independent review convergence.

## Implementation phases and parallel execution

`plan.md` and `tasks.md` are the implementation execution authority.

PowerPack does not create a second task scheduler. Before implementation it validates phase ordering and then delegates execution to upstream `speckit.implement`, which:

- completes phases in order;
- respects task dependencies;
- executes test tasks before corresponding implementation tasks when TDD is requested;
- may run tasks explicitly marked `[P]` in parallel;
- keeps same-file or dependency-related work sequential;
- marks completed tasks `[X]`.

PowerPack never invents parallelism beyond `[P]`.

## Mandatory review remediation

Every valid review finding is current-delivery work regardless of severity or wording: errors, warnings, suggestions, nits, hardening observations and documentation findings are mandatory once emitted.

The remediation planner first updates SPEC traceability and creates dependency-correct tasks covering implementation/configuration, tests/verification and project documentation. Those tasks are then executed by `speckit.implement` under the same phase/dependency/`[P]` rules.

Findings cannot be deferred to backlog, TODO, technical debt or a future SPEC. Approval requires zero findings.

## Development installation

Use development mode only when actively modifying PowerPack itself.

```bash
specify extension add --dev "$POWERPACK_REPO/extensions/powerpack"
specify workflow add --dev "$POWERPACK_REPO/workflows/powerpack-delivery"
```

The custom workflow step is still installed through the Spec Kit step-catalog mechanism. For local step development, serve a temporary maintainer-controlled catalog over HTTP/HTTPS or publish a development release; do not mix a local extension/workflow with an unrelated released step version.

For normal consumers, prefer the immutable release installation above.

## Update

Install the new versioned extension/workflow assets and register the matching versioned step catalog. Keep all three components on the same PowerPack version, then run `speckit.powerpack.doctor`.

## Uninstall

```bash
specify workflow remove powerpack-delivery
specify workflow step remove powerpack-control
specify extension remove powerpack
specify workflow step catalog remove powerpack
```

Removal does not delete feature SPECs or product code produced by previous delivery runs.
