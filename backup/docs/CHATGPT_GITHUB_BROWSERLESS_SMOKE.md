# Browserless GitHub smoke

## Purpose

This smoke is the GitHub counterpart of the recovered Project-context smoke. It stays on
the Codex/backend path. It does **not** reconstruct ChatGPT Web `/f/conversation`,
Playwright, CDP or Web2API.

```text
1. Resolve the installed GitHub plugin/connector through backend reads
2. Confirm OAuth is ACTIVE for that connector
3. Send `@GitHub LISTE TODOS OS MEUS REPOSITORIOS ... POWERPACK_GITHUB_TOOL_OK`
   through POST /backend-api/codex/responses
4. Pass only if the Codex stream contains a GitHub tool/function call and the marker
```

`@GitHub` in the prompt is a capability hint. It is not composer state. If the account
has GitHub installed but `/codex/responses` never invokes a GitHub tool, the smoke
fails closed as `GITHUB_TOOL_NOT_MATERIALIZED`. That is an expected browserless
boundary, not a Project-binding bug.

The existing `review smoke --flow web` remains unchanged.

## Commands

CLI:

```bash
speckit-powerpack review smoke \
  --flow github \
  --path "$TARGET" \
  --model gpt-5.6-sol \
  --effort high \
  --timeout 300
```

Standalone:

```bash
uv run python scripts/homologation/smoke_chatgpt_github_browserless.py \
  --include-assistant-text
```

## Classification

| Result | Meaning |
| --- | --- |
| `GITHUB_BROWSERLESS_SMOKE_PASSED` | Preflight passed and a GitHub tool call was observed. |
| `GITHUB_CONNECTOR_PREFLIGHT_FAILED` | Plugin/connector/OAuth could not be proven. |
| `GITHUB_TOOL_NOT_MATERIALIZED` | Plugin is installed, but this transport did not invoke GitHub. |
| `GITHUB_BROWSERLESS_SMOKE_INCOMPLETE` | Tool ran, but the response marker was missing. |
