# Browserless GitHub repository-list smoke via Codex Apps

This smoke validates a narrower capability than `smoke_chatgpt_github_codex_apps.py`: it does **not** use ChatGPT Project context and does not start from a known repository. Its only functional request is the equivalent of:

```text
liste todos os meus repositorios
```

The smoke resolves the installed GitHub connector through the account preflight, then explicitly selects it in the Codex turn using:

```text
[$github](app://<connector-id>)
```

The actual tool exposure, MCP execution, approvals and continuation are delegated to the installed Codex runtime through:

```text
codex exec --json --ephemeral --sandbox read-only
```

No browser, CDP, Playwright, Web2API or direct `/backend-api/codex/responses` submit is used by the smoke.

## PASS contract

A PASS requires all of the following:

- GitHub account/plugin preflight passes;
- the exact resolved connector is present in the `app://` mention;
- at least one `codex_apps` MCP call completes successfully;
- at least one completed `codex_apps` call contains a tool result;
- the MCP event is attributable to GitHub;
- no `command_execution` event occurs;
- no `web_search` event occurs;
- the turn completes and does not fail;
- the final response contains one unique `REPO owner/name` line per repository;
- the final `TOTAL N` equals the number of unique `REPO` lines;
- the final marker `POWERPACK_GITHUB_LIST_REPOS_OK` is present.

This self-consistency contract proves that the connector was used and that the assistant returned a complete list *according to the selected connector's own enumeration*. It does not independently enumerate the GitHub account through a second transport, so it deliberately does not claim external completeness beyond the connector's accessible scope.

## Run

```bash
cd /home/david/workspace/speckit-powerpack

uv run --extra dev python -m pytest -q \
  tests/test_github_connector_discovery.py \
  tests/test_chatgpt_github_list_repos_codex_apps_smoke_contract.py
```

Then run the functional smoke from any existing local working directory; no ChatGPT Project binding is required:

```bash
uv run python \
  scripts/homologation/smoke_chatgpt_github_list_repos_codex_apps.py \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --include-repositories \
  --include-assistant-text

echo "EXIT=$?"
```

Expected success classification:

```text
CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_SMOKE_PASSED
```

Relevant evidence includes:

```text
github_tool_call_observed = true
github_tool_result_observed = true
github_identity_in_event = true
no_local_shell_fallback = true
no_web_search_fallback = true
repository_listing.format_contract_passed = true
turn_completed = true
turn_failed = false
codex_exit_code = 0
```
