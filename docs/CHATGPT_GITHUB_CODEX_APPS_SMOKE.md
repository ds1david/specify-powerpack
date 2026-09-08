# Browserless GitHub connector smoke through Codex Apps

This smoke proves that the installed/authenticated GitHub app can be used by the Codex runtime without Chrome, CDP, Playwright, Web2API, or a hand-built `/backend-api/codex/responses` request.

## Why this path

The historical browserless Project smoke proved that PowerPack can read ChatGPT Project metadata/conversations with `~/.codex/auth.json` and serialize that context into a model request. That is not a native ChatGPT Project binding for the generated turn.

GitHub is different: discovery of an installed ChatGPT plugin/app is not sufficient evidence that the model received or invoked its tools. The current Codex runtime supports explicit app mentions in the form:

```text
[$app-name](app://<connector-id>)
```

and maps installed apps to MCP tools provided by the `codex_apps` MCP runtime.

The smoke therefore delegates app binding, tool exposure, approval policy, MCP execution, and continuation to the installed Codex CLI instead of reimplementing that protocol in PowerPack.

## Pipeline

```text
~/.codex/auth.json
        |
        +--> ChatGPT account/plugin preflight
        |      GET  /backend-api/ps/plugins/installed
        |      GET  /backend-api/ps/plugins/<plugin>
        |      POST /backend-api/apps/content?platform=chat
        |      POST /backend-api/aip/connectors/links/list_accessible
        |      POST /backend-api/apps/availability?platform=chat
        |             |
        |             +--> canonical GitHub connector id (kept in memory)
        |
        +--> ChatGPT Project backend reads
        |      GET /backend-api/gizmos/<project>
        |      GET /backend-api/gizmos/<project>/conversations
        |      GET /backend-api/conversation/<conversation>
        |             |
        |             +--> serialized Project context
        |
        +--> codex exec --json --ephemeral --sandbox read-only
               prompt contains [$github](app://<connector-id>)
                       |
                       +--> Codex Apps runtime
                       +--> codex_apps MCP tools
                       +--> MCP tool call / result
                       +--> final assistant response
```

The account/plugin preflight is useful but is not by itself the Codex tool-use gate. The runtime evidence from `codex exec --json` is the gate.

## Project semantics

The smoke reports:

```text
project_context_serialized = true
native_project_binding     = false
response_visible_in_project = false
```

The existing `.specify/powerpack/review.json` binding tells PowerPack which Project context to read. The generated Codex turn itself is not a native turn inside that ChatGPT Project.

## GitHub semantics

The prompt explicitly binds the discovered connector:

```text
[$github](app://<connector-id>)
```

The connector id is never printed in the report.

The prompt requests a minimal read-only access check against the GitHub repository derived from `remote.origin.url` (or supplied with `--github-repo owner/name`). It forbids shell, local-checkout answers, web search, other apps, and GitHub mutations.

## PASS contract

PASS requires all of the following:

```text
GitHub ChatGPT-side discovery            PASS
Project context read/serialization       PASS
explicit app:// GitHub mention           PASS
codex exec exit code                     0
codex_apps MCP completed call            >= 1
codex_apps MCP result                    >= 1
local shell fallback                     0
web search fallback                      0
turn.completed                           true
turn.failed                              false
final marker                             present
requested owner/repo                     present in final answer
```

The final marker is:

```text
POWERPACK_GITHUB_CONNECTOR_OK owner/repo
```

Text mentioning GitHub without a structural `mcp_tool_call` does not pass.

## Classifications

- `CHATGPT_GITHUB_CODEX_APPS_SMOKE_PASSED`
- `CHATGPT_GITHUB_CODEX_APPS_TOOL_UNAVAILABLE`
- `CHATGPT_GITHUB_CODEX_APPS_FALLBACK_DETECTED`
- `CHATGPT_GITHUB_CODEX_APPS_SMOKE_CONTRACT_FAILED`
- `CHATGPT_GITHUB_CODEX_APPS_SMOKE_BLOCKED`

## Preconditions

1. Codex CLI is installed and logged in (`~/.codex/auth.json`).
2. The target repository is already materialized with PowerPack.
3. The target repository is bound to a ChatGPT Project with:

```text
provider      = chatgpt-project
mode          = backend-api
authorization = codex-backend-api
project_id    = g-p-...
```

4. The GitHub plugin/app is installed and authorized on the same ChatGPT account.
5. The Codex version in use supports Apps/Connectors (`app://...`) and JSONL `mcp_tool_call` events.

## Contract tests

From the PowerPack checkout:

```bash
uv run --extra dev python -m pytest -q \
  tests/test_github_connector_discovery.py \
  tests/test_chatgpt_github_codex_apps_smoke_contract.py
```

Do not claim PASS until this output is observed in the target environment.

## Functional smoke

```bash
uv run python \
  scripts/homologation/smoke_chatgpt_github_codex_apps.py \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --include-assistant-text

echo "EXIT=$?"
```

If the target origin is not `github.com`, specify the repository explicitly:

```bash
uv run python \
  scripts/homologation/smoke_chatgpt_github_codex_apps.py \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --github-repo ds1david/autonomous-trading-strategy-evolution-lab \
  --include-assistant-text
```

## Security

The smoke does not print access tokens, account ids, OAuth link ids, plugin ids, or the canonical connector id. It does not fabricate or replay Sentinel/proof/Turnstile material. The Codex process owns the Apps/MCP execution lifecycle.
