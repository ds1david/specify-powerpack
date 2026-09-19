# PowerPack installation and usage

This document is the supported operator path for installing and using Specify PowerPack in an existing Spec Kit project.

## Prerequisites

- Spec Kit `specify >= 1.0.0`.
- An initialized project with `.specify/init-options.json` and an active integration.
- Git with a `github.com` `origin`.
- Codex CLI authenticated with `codex login`.
- Exactly one enabled and available GitHub App/connector for independent review.
- A local checkout of this PowerPack repository for installation. The custom workflow step is installed through the PowerPack step catalog because current Spec Kit installs third-party steps through a step catalog.

PowerPack supports the same script choice selected by `specify init`: `sh`, `ps` or `py`.

## Install

From the target Spec Kit project, set `POWERPACK_REPO` to the checkout of this repository.

### 1. Install the extension

```bash
specify extension add --dev "$POWERPACK_REPO/extensions/powerpack"
```

The extension registers the two public commands with the active integration:

- `speckit.powerpack.deliver`
- `speckit.powerpack.doctor`

If the active integration is changed later, run the normal Spec Kit integration switch/use flow so enabled extension commands are re-registered for the new active integration.

### 2. Register the PowerPack step catalog

```bash
specify workflow step catalog add \
  https://raw.githubusercontent.com/ds1david/specify-powerpack/main/catalogs/step-catalog.json \
  --name powerpack \
  --install-allowed
```

This catalog is intentionally narrow: it publishes only the `powerpack-control` custom step and its package files.

### 3. Install the PowerPack control step

```bash
specify workflow step add powerpack-control
```

### 4. Install the delivery workflow

```bash
specify workflow add --dev "$POWERPACK_REPO/workflows/powerpack-delivery"
```

### 5. Validate the installation

Invoke the command through the active integration.

Logical command:

```text
speckit.powerpack.doctor
```

For Codex skills mode the materialized command normally uses the `$` skill prefix and a hyphenated skill name, for example:

```text
$speckit-powerpack-doctor
```

Run the normal doctor with network validation. It checks the GitHub App because review cannot succeed without it. Use `--offline` only for an intentionally disconnected diagnostic.

A healthy installation exits zero and ends with `HEALTHY`.

## Use the delivery workflow

For a new feature, pass a feature description:

```text
speckit.powerpack.deliver Implement ...
```

For an existing feature, pass the SPEC id/name used by the project:

```text
speckit.powerpack.deliver spec-soak-003
```

For Codex skills mode the corresponding materialized skill is normally:

```text
$speckit-powerpack-deliver spec-soak-003
```

PowerPack may adopt work already completed manually. It preserves valid SPEC/plan/tasks artifacts, converges reviewer-owned checklists, re-runs analyze as a freshness pass, implements pending tasks, runs Spec Kit converge until `tasks.md` stabilizes, prepares the exact PR/HEAD and then enters independent review convergence.

## Mandatory review remediation

Every review finding is current-delivery work. Severity or wording does not create an exception: errors, warnings, suggestions, nits, hardening observations and documentation findings are all mandatory once emitted by the independent review.

For each finding the remediation cycle must:

1. implement the required change in code/configuration/tests as applicable;
2. update project documentation describing the affected behavior or operation;
3. update the active SPEC artifacts when the finding changes, clarifies or closes a requirement, contract, acceptance criterion, task or operational invariant;
4. re-run Spec Kit convergence;
5. republish the exact PR HEAD;
6. re-run independent review.

Findings cannot be deferred to backlog, TODO, technical debt or a future SPEC. Approval requires zero findings.

## Update

For a local-development installation, refresh all three installed primitives after updating the PowerPack checkout:

```bash
specify extension add --dev "$POWERPACK_REPO/extensions/powerpack" --force
specify workflow step remove powerpack-control
specify workflow step add powerpack-control
specify workflow add --dev "$POWERPACK_REPO/workflows/powerpack-delivery"
```

Then run `speckit.powerpack.doctor` again.

## Uninstall

```bash
specify workflow remove powerpack-delivery
specify workflow step remove powerpack-control
specify extension remove powerpack
specify workflow step catalog remove powerpack
```

Removal does not delete feature SPECs or product code produced by previous delivery runs.
