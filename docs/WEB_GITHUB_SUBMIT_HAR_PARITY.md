# GitHub final-submit HAR parity experiment

## Current proven boundary

The WSL browserless probe suite passed with:

```text
33 passed in 0.19s
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

## Next controlled probe

`scripts/homologation/probe_chatgpt_github_conversation_submit_har_parity.py` performs one final submit using:

```text
all previously proven connector/mention/conduit fields
+ create_time
+ model_response_contracts
+ client_contextual_info
+ paragen_cot_summary_display_override
+ force_parallel_switch
+ thinking_effort
+ local_function_names
```

while still omitting all Sentinel/proof/Turnstile values.

Interpretation:

```text
HTTP 200 + structural GitHub tool evidence
  -> final connector materialization proven

HTTP 422
  -> body or request-contract parity is still incomplete
  -> do not conclude Sentinel is mandatory yet

HTTP 401/403 after body parity
  -> authentication/product turn-security boundary becomes the leading explanation
  -> do not attempt to bypass it
```

The probe emits only redacted evidence and never prints connector ids, conduit tokens, OAuth/session secrets, or raw security diagnostics.
