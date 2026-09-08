# Complete ChatGPT Web GitHub conversation HAR findings

## Capture

A complete Edge HAR was captured after the user:

1. opened a new ChatGPT conversation;
2. selected the desired model/reasoning level;
3. pasted exactly:

```text
@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK
```

4. clicked Send; and
5. waited until the response completed.

The raw HAR is sensitive evidence and must not be committed. This document records only structural/non-secret findings.

## Main correction

The Web product did **not** require the user to manually open Plugins → GitHub before sending this turn.

After the literal `@GitHub` text entered the composer, the frontend performed two preparation phases:

```text
plain composer text
  -> prepare with system_hints=[] and literal @GitHub in partial_query
  -> frontend resolves the ecosystem mention
  -> conversation/init with plugin:connector_<github-id>
  -> prepare with plugin system_hint and @GitHub removed from partial_query text
  -> final Send with structured ecosystemMention metadata
```

Therefore the preferred CDP experiment is now:

```text
insert the complete @GitHub prompt
  -> wait for frontend connector materialization
  -> verify connector-aware prepare/context-change evidence
  -> only then click Send
```

A manual Plugins-menu selection remains a possible fallback if `Input.insertText` does not trigger the same mention-resolution behavior as a real paste, but it is no longer the primary hypothesis.

## Observed request sequence

### A. Model/reasoning state already selected

Before the final prompt was sent, the composer preparation traffic already used:

```text
model = gpt-5.6-sol-wm
thinking_effort = xhigh
conversation_origin = tpp
```

These are private product values observed in this capture. They are **not** stable public API identifiers and must not be promoted to universal constants.

The important contract is that the final turn uses the model/reasoning state selected by the Web UI. Do not substitute `conversation/init.default_model_slug` blindly.

In this capture, `conversation/init` returned:

```text
default_model_slug = gpt-5-6-thinking
```

while the actual prepared/submitted turn used:

```text
model = gpt-5.6-sol-wm
thinking_effort = xhigh
```

That difference invalidates the prior assumption that the init default model can be reused as the final submit model.

### B. First conversation init — no GitHub connector yet

```http
POST /backend-api/conversation/init
```

```json
{
  "requested_default_model": null,
  "conversation_id": null,
  "timezone": "America/Sao_Paulo",
  "timezone_offset_min": 180,
  "conversation_origin": "tpp"
}
```

No GitHub `system_hints` were present at this stage.

### C. Composer prepare — literal `@GitHub`, connector unresolved

```http
POST /backend-api/f/conversation/prepare
```

Relevant fields:

```text
action = next
parent_message_id = client-created-root
model = gpt-5.6-sol-wm
client_prepare_state = none
client_prepare_dispatch = debounced
client_prepare_source = composer_editor_state
system_hints = []
partial_query.id = <client UUID>
partial_query.content.parts[0] = @GitHub LISTE ... POWERPACK_GITHUB_TOOL_OK
conversation_origin = tpp
thinking_effort = xhigh
```

The response was HTTP 200 with:

```text
status = ok
conduit_token = <secret, not retained>
```

This first conduit is not the final connector-aware turn token.

### D. Connector materialization

Immediately after the composer resolved the mention, the frontend sent another:

```http
POST /backend-api/conversation/init
```

now with:

```json
{
  "system_hints": [
    "plugin:connector_<github-id>"
  ]
}
```

The connector id is resolved dynamically by the ChatGPT account/plugin state and must never be hard-coded.

### E. Connector-aware prepare

At essentially the same moment, the frontend sent:

```http
POST /backend-api/f/conversation/prepare
```

with:

```text
parent_message_id = client-created-root
model = gpt-5.6-sol-wm
client_prepare_state = sent
client_prepare_dispatch = immediate
client_prepare_source = context_change
system_hints = [plugin:connector_<github-id>]
partial_query.id = <different client UUID>
partial_query.content.parts[0] = GitHub LISTE ... POWERPACK_GITHUB_TOOL_OK
conversation_origin = tpp
thinking_effort = xhigh
```

Important: the structured partial query no longer includes the leading `@` symbol. The final message still does.

The response again returned HTTP 200 with:

```text
status = ok
conduit_token = <secret>
```

### F. Final conversation submit — accepted

```http
POST /backend-api/f/conversation
Accept: text/event-stream
```

The successful final body used:

```text
parent_message_id = client-created-root
model = gpt-5.6-sol-wm
client_prepare_state = success
conversation_origin = tpp
thinking_effort = xhigh
```

and the message contained both the literal text and structural connector metadata:

```json
{
  "content": {
    "parts": [
      "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK"
    ]
  },
  "metadata": {
    "system_hints": [
      "plugin:connector_<github-id>"
    ],
    "serialization_metadata": {
      "custom_symbol_offsets": [
        {
          "id": "plugin:connector_<github-id>",
          "symbol": "ecosystemMention",
          "startIndex": 0,
          "endIndex": 7
        }
      ]
    },
    "submission_mode": "manual_send"
  }
}
```

The top-level body also repeated:

```text
system_hints = [plugin:connector_<github-id>]
```

The request returned HTTP 200.

## Critical bug found in the existing browserless probes

The prepare endpoint returns:

```json
{"status":"ok", "conduit_token":"..."}
```

but the real final submit sends:

```json
{"client_prepare_state":"success"}
```

Therefore this probe logic is incorrect:

```python
prepare_state = prepare["status"]  # produces "ok"
```

`prepare.status` and final `client_prepare_state` are **not the same field/semantic value**.

The earlier browserless 422 experiments that propagated `"ok"` into the final body were not exact HAR parity tests.

## Other missing parity fields in the earlier probes

The complete HAR proves that earlier probes also diverged in these areas:

```text
conversation_origin = tpp                    missing
actual selected model = gpt-5.6-sol-wm       different
thinking_effort = xhigh                      different
prepare state/source/dispatch sequence       different
initial unresolved @GitHub prepare           omitted
connector context-change prepare             only partially reproduced
```

These differences must be fixed before HTTP 422 can be used to infer a security-header boundary.

## Final response transport

The accepted `POST /backend-api/f/conversation` did not stream the full assistant answer directly in the captured HTTP body. Its SSE returned a handoff containing:

```text
resume_conversation_token
conversation_id
turn_exchange_id
resume/subscribe topic options
```

and then `[DONE]`.

The conversation later reported:

```http
GET /backend-api/conversation/<id>/stream_status
```

```json
{"status":"COMPLETE"}
```

The HAR does not preserve the realtime payload that carried the complete generated answer/tool lifecycle. This is another reason the CDP/Web2API path is attractive: it can observe the actual browser turn and read the completed response from DOM/conversation state instead of reimplementing the private realtime handoff.

## Sentinel/security observation

The successful final request contained Sentinel/proof/Turnstile-related headers generated by the real Web product.

This capture still does not prove whether those headers are required for schema validation, authorization, anti-abuse enforcement, or some combination. PowerPack must not fabricate or replay them.

The correct experiment order remains:

1. reproduce the now-known exact non-secret turn semantics;
2. if the direct browserless submit still fails, record the boundary;
3. do not bypass product-security mechanisms;
4. prefer CDP/Web UI transport when the frontend can legitimately generate the required turn state.

## Corrected CDP flow

```text
navigate to target ChatGPT Project/new conversation
  -> select configured model/reasoning through supported UI state
  -> Network.enable before composer mutation
  -> insert complete prompt beginning with @GitHub
  -> DO NOT click Send immediately
  -> wait for connector materialization evidence:
       conversation/init system_hints contains GitHub connector
       connector-aware prepare has:
         client_prepare_source = context_change
         system_hints = plugin:connector_<github-id>
         partial query no longer starts with @GitHub
  -> only after that evidence, click Send
  -> capture final /f/conversation request
  -> require ecosystemMention + connector hints
  -> wait for completed assistant response
  -> require evidence that exact GitHub target/PR was actually inspected
```

### `Input.insertText` caveat

The HAR proves that a real paste triggers mention resolution. It does **not** yet prove that CDP `Input.insertText` triggers the same frontend behavior.

Therefore the first CDP homologation should test this explicitly:

```text
Input.insertText(full @GitHub prompt)
  -> wait for context-change connector prepare
```

If it appears, no explicit Plugins-menu automation is needed.

If it does not appear within a bounded timeout, PowerPack should fail closed for that experiment and then test a real UI/plugin-selection fallback rather than sending an unstructured `@GitHub` message.
