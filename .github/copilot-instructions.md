# GitHub Copilot instructions for Specify PowerPack

## Project model

- Specify PowerPack extends GitHub Spec Kit; it does not replace, fork, bootstrap, or own the Spec Kit lifecycle unless an accepted specification explicitly says otherwise.
- Treat accepted SPECs as the authority for supported PowerPack behavior. Distinguish a real defect from a new capability request; do not silently resurrect behavior removed by an accepted SPEC.
- Read `.specify/integration.json` or the native `specify integration` commands for integration state. Do not infer the active/default integration from agent-specific directories.
- Never switch the Spec Kit default integration, install/remove an integration, or change integration options unless the user explicitly requests that lifecycle change.

## Copilot integration model

- Prefer Copilot **skills mode** for Spec Kit (`.github/skills/speckit-*/SKILL.md`). Commands/agents mode is compatibility-only unless a task explicitly targets it.
- Treat Spec Kit-generated Copilot artifacts as derived files. Prefer changing the authoritative extension/preset/template source and using the native Spec Kit lifecycle to rescaffold generated skills.
- Installing Copilot as an additional integration does not imply that it becomes the default integration.
- Extensions and presets are materialized for the active/default integration. Do not claim that a non-default Copilot integration has current PowerPack skills unless the generated Copilot artifacts have actually been refreshed through the Spec Kit lifecycle.

## PowerPack skill boundaries

- PowerPack skills must remain agent-agnostic at the semantic level. Copilot-specific files are adapters, not the source of business/workflow authority.
- Do not hard-code a portable skill to one agent's tool names. Select tools by capability and permitted effect.
- More available tools never imply more decision authority.
- `checklist-converge`-style requirements work may read/search broadly, but may write only deterministic requirements/design repairs authorized by existing requirements. It must not modify application code/tests or invent product/security/business intent.
- Review-only operations must not mutate the repository unless the accepted workflow explicitly includes a repair phase.

## Tool and permission policy

- Default to least privilege for Copilot CLI. Do not add `--yolo`, `--allow-all`, `--allow-all-tools`, or equivalent broad permission flags unless the user explicitly requests unrestricted execution in an isolated environment.
- Repository instructions are behavioral guardrails, not a security boundary. Use actual Copilot CLI permission controls when a task requires enforcement.
- Remote/destructive actions such as `git push`, merging/closing PRs, deleting remote resources, publishing packages/releases, changing secrets, or modifying external systems require explicit user intent for that action.
- Never persist credentials, OAuth tokens, cookies, API keys, or authentication material in repository configuration or PowerPack workflow state.
- Do not persist PowerPack workflow state through `.bashrc`, `.zshrc`, PowerShell profiles, Windows global/user environment, or equivalent host configuration.

## State and hooks

- Durable PowerPack workflow facts belong in project-local JSON state owned by PowerPack.
- Environment variables are temporary process/child-process projections only. Do not assume an ENV value exported by one hook survives into an independent hook, parent agent, or later session.
- Validate state schema, source-artifact identity/fingerprints, freshness, and revision before a consequential workflow decision.
- Use atomic replacement plus conflict/lost-update detection for concurrently writable state.

## Canvas and visual integrations

- GitHub Copilot Canvas is an optional UI adapter. It may read PowerPack machine-readable state and invoke registered PowerPack skills, but it must not become a second implementation of PowerPack workflow semantics.
- Do not assume a PowerPack skill appears automatically in the upstream Spec Kit SDD Canvas. Canvas integration requires an explicit adapter/change because the current SDD Canvas models an explicit stage/command set.

## Repository workflow

- Respect the root `AGENTS.md` instructions, including Graphify requirements when applicable.
- Keep separate SPECs independently reviewable unless an accepted requirement explicitly establishes a hard dependency.
- Prefer one focused branch/PR per SPEC or infrastructure concern.
- When changing generated Spec Kit integration artifacts, verify whether the native `specify integration/extension/preset` lifecycle should perform the change instead of hand-editing the generated file.
