# Browserless GitHub conversation probe status

## Purpose

This file records the current evidence for the browserless ChatGPT/GitHub transport experiments on `feat/homologation-harness`.

The transport uses the authenticated ChatGPT account derived from `~/.codex/auth.json`. It does not use Playwright, Chromium, copied browser cookies, hard-coded connector ids, or fabricated Sentinel/proof material.

## Proven on WSL

The user most recently proved the combined suite before the complete-HAR additions with:

```text
41 passed in 0.19s
```

The read-only GitHub connector preflight remains proven:

```text
GitHub plugin dynamically resolved          PASS
GitHub connector dynamically resolved       PASS
connector metadata ENABLED                  PASS
connector type SERVICE                      PASS
OAuth accessible link present               PASS
OAuth auth_status ACTIVE                    PASS
connector_status ENABLED                    PASS
apps_privacy_control full_access             PASS
app installed                               PASS
app available                               PASS
```

The following browserless boundaries are also proven:

```text
conversation/init + connector hint          PASS
conversation/prepare + connector hint       PASS
legitimate conduit_token returned           PASS
```

## Correction from the complete successful Web HAR

A newer complete Edge HAR captured the full manual flow:

```text
new conversation
-> model/reasoning selected
-> paste @GitHub ... POWERPACK_GITHUB_TOOL_OK
-> Send
-> wait for complete response
```

That HAR proved that the earlier browserless final-submit probes were **not exact body/turn parity tests**.

### Actual Web turn sequence

The frontend first prepared the literal composer text with GitHub unresolved:

```text
prepare
  system_hints = []
  partial_query starts with @GitHub
  client_prepare_state = none
  client_prepare_dispatch = debounced
  client_prepare_source = composer_editor_state
```

Then the frontend resolved the ecosystem mention and performed a connector context change:

```text
conversation/init
  system_hints = [plugin:connector_<github-id>]

prepare
  system_hints = [plugin:connector_<github-id>]
  partial_query starts with GitHub (no leading @)
  client_prepare_state = sent
  client_prepare_dispatch = immediate
  client_prepare_source = context_change
```

Only after that did the accepted final submit occur.

### Critical prepare-state bug in old probes

The prepare HTTP response is:

```json
{"status":"ok", "conduit_token":"..."}
```

but the accepted final body uses:

```json
{"client_prepare_state":"success"}
```

Therefore the old mapping:

```python
client_prepare_state = prepare_response["status"]
```

was wrong. `status=ok` and final `client_prepare_state=success` are distinct protocol semantics.

### Other parity differences discovered

The complete HAR also showed:

```text
conversation_origin = tpp
actual final model = gpt-5.6-sol-wm
thinking_effort = xhigh
```

while `conversation/init` reported:

```text
default_model_slug = gpt-5-6-thinking
```

Therefore the init default model must not be blindly reused as the final turn model. The real Web turn uses the model/reasoning state selected in the UI.

The earlier browserless probes also omitted the initial unresolved `@GitHub` prepare and did not reproduce the exact connector context-change sequence.

## Consequence for the previous HTTP 422 evidence

The previous direct final-submit results remain factual:

```text
POST /backend-api/f/conversation -> HTTP 422
{"detail":"Invalid conversation body"}
```

but they no longer qualify as exact successful-HAR parity experiments.

Do **not** infer from those 422s that Sentinel/proof/Turnstile is required. First reproduce the corrected non-secret turn semantics.

The new probe is:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_complete_har_flow.py
```

It reproduces:

```text
initial init without connector
unresolved @GitHub prepare
connector discovery
connector init
connector context-change prepare
final client_prepare_state = success
conversation_origin = tpp
observed HAR model/reasoning values by default
structured ecosystemMention
legitimate connector-aware conduit token
```

It still deliberately omits Sentinel/proof/Turnstile values and browser-cookie material.

## Successful Web submit and response handoff

The complete HAR's final request returned HTTP 200.

The initial SSE response did not contain the full assistant answer. It returned a private stream handoff with:

```text
resume_conversation_token
conversation_id
turn_exchange_id
resume/subscribe topic options
```

and then `[DONE]`.

Later:

```http
GET /backend-api/conversation/<id>/stream_status
```

returned:

```json
{"status":"COMPLETE"}
```

The HAR did not preserve the realtime payload containing the complete assistant/tool stream. Browserless transport will therefore require additional handoff/realtime work even after a successful HTTP 200 final submit.

The CDP/Web2API path avoids needing to clone that private realtime transport because it can observe the real Web conversation and retrieve the completed response through its existing DOM/conversation mechanisms.

## Corrected CDP hypothesis

The complete HAR proves that a real paste of the full `@GitHub` prompt automatically caused connector materialization before Send.

Preferred CDP experiment:

```text
navigate to target Project/new conversation
-> select intended model/reasoning
-> Network.enable
-> Input.insertText(full @GitHub prompt)
-> DO NOT click Send immediately
-> wait for connector-aware context-change prepare
-> verify plugin:connector_<github-id>
-> only then click Send
-> capture accepted final /f/conversation
-> verify ecosystemMention metadata
-> wait for completed response
```

Caveat: the HAR proves real browser paste behavior, not yet CDP `Input.insertText` behavior. If `Input.insertText` does not trigger connector materialization, the next fallback experiment is explicit UI/plugin selection.

## Current H2 classification

```text
ChatGPT auth                              PASS
ChatGPT Project discovery/binding         PASS
Project-context transport                 PASS
PR identity contract                      PASS
GitHub plugin discovery                   PASS
GitHub connector dynamic resolution       PASS
GitHub OAuth ACTIVE                       PASS
GitHub app installed/available            PASS
conversation/init + connector hint        PASS
conversation/prepare + conduit            PASS
old final-submit 422                      PROVEN BUT NOT EXACT HAR PARITY
complete-HAR browserless submit           PENDING RE-RUN
CDP Input.insertText mention resolution   PENDING
GitHub tool-call evidence                 PENDING
exact PR inspection                       PENDING
production Web PR review                  BLOCKED_CAPABILITY
H2 overall                                BLOCKED_CAPABILITY
```
