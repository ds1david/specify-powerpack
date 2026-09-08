# Isolated ChatGPT GitHub CDP probe

## Purpose

This probe tests the next architecture boundary after the browserless `/backend-api/f/conversation` experiment reached HTTP 403.

It does **not** reconstruct or replay the private ChatGPT conversation request. Instead it drives the real ChatGPT frontend through Chrome DevTools Protocol (CDP) and observes the request that the frontend itself produces.

The question under test is deliberately narrow:

```text
CDP Input.insertText("@GitHub ...")
  -> does the real ChatGPT frontend resolve @GitHub into connector context?
  -> if yes, does native Send produce /f/conversation HTTP 200?
  -> if yes, does the assistant finish with the expected marker?
```

This is a separate homologation experiment. It is not wired into the production review provider.

## Files

```text
scripts/homologation/probe_chatgpt_github_cdp.ps1
scripts/homologation/probe_chatgpt_github_cdp.sh
tests/test_chatgpt_github_cdp_probe_contract.py
```

## Architecture

When launched from WSL:

```text
WSL bash launcher
  -> powershell.exe on Windows
  -> dedicated Windows Chrome profile
  -> Chrome remote debugging on Windows localhost
  -> raw CDP websocket
  -> real chatgpt.com frontend
```

The PowerShell process and Chrome both run on Windows. WSL therefore does not need direct TCP access to the Windows CDP port.

The probe uses only CDP primitives and Windows PowerShell/.NET:

```text
Page.enable
Runtime.enable
Network.enable
Runtime.evaluate
Input.dispatchKeyEvent
Input.insertText
```

No Playwright dependency is required for this probe.

## What the probe does

1. Launch a dedicated Chrome profile with a local CDP port (default `9222`), unless `-NoLaunch` is supplied.
2. Open a new `https://chatgpt.com/` page target.
3. Wait until the real ChatGPT composer is available.
4. Enable CDP `Network` observation before changing the composer.
5. Focus/clear the new-chat composer.
6. Insert the complete prompt using CDP `Input.insertText`:

```text
@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK
```

7. Do **not** click Send yet.
8. Wait for a native frontend `POST /backend-api/f/conversation/prepare` whose body proves the connector context change:

```text
client_prepare_source = context_change
system_hints contains plugin:connector_<...>
partial_query starts with "GitHub "
```

9. If that evidence does not appear, fail closed as `CDP_GITHUB_MENTION_NOT_RESOLVED` and do not send the message.
10. If it appears, click the real ChatGPT Send button through the DOM.
11. Observe the native frontend `POST /backend-api/f/conversation` and require:

```text
top-level connector system_hint
message-level connector system_hint
ecosystemMention serialization metadata
HTTP 200 response
```

12. Poll the rendered assistant DOM through CDP until generation stops and the response contains:

```text
POWERPACK_GITHUB_TOOL_OK
```

The probe does not need to generate conduit, Sentinel, proof, Turnstile, cookies or private turn-security material. Those remain the responsibility of the real ChatGPT frontend.

## Security and logging

The probe intentionally does **not** log request headers.

It does not print or persist:

```text
Authorization
Cookie
OAuth/session tokens
connector ids
conduit tokens
Sentinel/proof/Turnstile values
raw request headers
```

It inspects only the non-secret request-body structure needed for capability evidence and emits booleans/status values.

Assistant response text is not included by default because the GitHub test can reveal private repository names. Use `-IncludeAssistantText` only when you explicitly want it in the local result.

## Run from WSL

Pull the branch and run the static contract test first:

```bash
cd /home/david/workspace/speckit-powerpack
git pull
git rev-parse HEAD

uv run --extra dev python -m pytest -q \
  tests/test_chatgpt_github_cdp_probe_contract.py
```

Then launch the isolated CDP probe:

```bash
bash scripts/homologation/probe_chatgpt_github_cdp.sh
echo "EXIT=$?"
```

The first run uses a dedicated persistent Chrome profile under:

```text
%LOCALAPPDATA%\SpecKitPowerPack\cdp-github-probe
```

If that profile is not logged into ChatGPT, complete the normal ChatGPT login in the Chrome window. The probe waits for the composer. If it times out during the first login, keep Chrome open and rerun without launching another browser:

```bash
bash scripts/homologation/probe_chatgpt_github_cdp.sh -NoLaunch
echo "EXIT=$?"
```

## Optional parameters

Use another local CDP port:

```bash
bash scripts/homologation/probe_chatgpt_github_cdp.sh -CdpPort 9333
```

Use a different ChatGPT URL (for example a known Project URL) once the generic connector test passes:

```bash
bash scripts/homologation/probe_chatgpt_github_cdp.sh \
  -ChatUrl 'https://chatgpt.com/g/g-p-.../project'
```

Include the final assistant text in the local JSON report:

```bash
bash scripts/homologation/probe_chatgpt_github_cdp.sh -IncludeAssistantText
```

This initial probe intentionally does not automate model/reasoning selection. Its first gate is only whether CDP text insertion triggers the same `@GitHub` connector-resolution behavior observed in the successful manual HAR. Model/reasoning automation should be added only after this gate passes.

## Classification

### Full probe success

```text
classification = CDP_GITHUB_FLOW_ACCEPTED
ok = true

cdp_connected                     true
composer_ready                    true
input_insert_text_used            true
github_context_change_prepare     true
connector_hint_present            true
partial_query_starts_with_github  true
send_clicked                      true
final_submit_observed             true
final_top_level_connector_hint    true
final_message_connector_hint      true
final_ecosystem_mention           true
final_http_status                 200
assistant_response_complete       true
marker_seen                       true
```

This proves the CDP/browser transport can materialize the GitHub connector and complete a native ChatGPT turn without hitting the browserless 403 boundary.

It is **not yet sufficient to classify H2 overall PASS**. A later PR-specific homologation still needs exact PR identity/inspection evidence and the independent-review contract.

### Mention not materialized

```text
classification = CDP_GITHUB_MENTION_NOT_RESOLVED
```

`Input.insertText` did not cause the frontend to produce the connector-aware `context_change` prepare. The probe deliberately does not click Send. The next experiment would then automate GitHub selection/mention creation through the real composer UI before appending the review prompt.

### Native submit rejected

```text
classification = CDP_FINAL_SUBMIT_REJECTED
```

The real frontend emitted the final conversation request but it did not return HTTP 200. Capture only redacted structural evidence; do not attempt to bypass product security.

### Authentication/composer blocked

```text
classification = BLOCKED_AUTHENTICATION_OR_COMPOSER
```

The dedicated Chrome profile is not logged in or the ChatGPT composer did not become usable. Complete normal login in the visible browser and rerun with `-NoLaunch`.
