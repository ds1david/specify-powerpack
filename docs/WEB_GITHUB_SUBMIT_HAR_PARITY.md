# GitHub final-submit HAR parity experiment

## Current proven boundary

The WSL browserless probe suite passed with:

```text
36 passed in 0.19s
```

The authenticated flow has proven:

```text
GitHub connector discovery                 PASS
GitHub OAuth/app availability              PASS
POST /backend-api/conversation/init        PASS
POST /backend-api/f/conversation/prepare   PASS
legitimate conduit_token returned          PASS
POST /backend-api/f/conversation            HTTP 422
```

The safe 422 diagnostic returned only:

```json
{
  "detail": "Invalid conversation body"
}
```

There were no field-level validation locations/messages. Therefore the 422 cannot be attributed to Sentinel/proof/Turnstile. It only proves that the final request was rejected before GitHub tool execution was demonstrated.

## Successful Edge HAR body parity

The successful ChatGPT Web request contained the connector/mention fields already used by the initial submit probe plus these additional non-secret body fields:

```text
messages[0].create_time
model_response_contracts
client_contextual_info
paragen_cot_summary_display_override
force_parallel_switch
thinking_effort
local_function_names
```

Observed structural/value examples suitable for a controlled browserless experiment:

```text
model_response_contracts:
  id = photo_upload_action.v1
  protocol_version = 1
  presets = cap:image, cap:file, placement:end

client_contextual_info:
  app_name = chatgpt.com
  browser/UI telemetry fields with scalar values

paragen_cot_summary_display_override = allow
force_parallel_switch = auto
thinking_effort = extended
local_function_names = [local.continue_in_work]
```

The successful browser request also carried Sentinel/proof/Turnstile-related headers. Those values are not part of this parity experiment and must not be fabricated, replayed, logged or persisted.

## HAR-shape result

The broader HAR-shape probe reproduced the non-secret prepare and submit fields above and still returned:

```text
classification = REQUEST_VALIDATION_REJECTED
HTTP status     = 422
detail          = Invalid conversation body
```

Therefore generic field presence is not sufficient. The next comparison must focus on cross-field semantics that can be validated by the backend.

## Newly isolated cross-field difference

The successful Edge HAR uses this special root identity for a new conversation:

```text
parent_message_id = client-created-root
```

The same value is present in the successful prepare request and the successful final `/f/conversation` request.

The previous browserless probes instead generated an arbitrary UUID for `parent_message_id`. Although `/f/conversation/prepare` accepted that UUID, the final endpoint may apply stricter conversation-body validation.

A second safe difference exists in the successful prepare payload:

```text
partial_query.id = <client-generated UUID>
```

The previous prepare probes omitted that id. In the successful HAR, `partial_query.id` is not the same id as the final user message, so it should be treated as independent composer state rather than message identity.

## Next controlled probe: root parity

`scripts/homologation/probe_chatgpt_github_conversation_root_parity.py` isolates these semantics without adding browser credentials or product-security headers.

Run first with only root parity:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_conversation_root_parity.py
```

If that still returns 422, run the second ablation with the HAR-observed `partial_query.id`:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_conversation_root_parity.py \
  --include-partial-query-id
```

Interpretation:

```text
HTTP 200 + structural GitHub tool evidence
  -> final connector materialization proven

HTTP 200 without structural GitHub tool evidence
  -> transport/body accepted, but GitHub tool use still not proven

HTTP 422 with root parity only
  -> root identity alone is insufficient
  -> test partial_query.id next

HTTP 422 with root + partial_query.id
  -> another body/cross-field invariant remains missing
  -> do not conclude Sentinel is mandatory yet

HTTP 401/403/429 after parity
  -> request crossed body validation into an auth/security/rate boundary
  -> do not attempt to bypass it
```

The probe emits only redacted evidence and never prints connector ids, conduit tokens, OAuth/session secrets, browser cookies, or raw security diagnostics.
