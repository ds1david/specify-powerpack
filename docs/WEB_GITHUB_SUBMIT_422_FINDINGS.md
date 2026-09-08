# Browserless GitHub final-submit HTTP 422 findings

## Status

The connector-aware browserless experiment has now proven, on WSL with Codex-derived ChatGPT authentication:

```text
GitHub plugin discovery                  PASS
GitHub connector dynamic resolution      PASS
GitHub OAuth ACTIVE                      PASS
GitHub app installed/available           PASS
conversation/init + connector hint       PASS
conversation/prepare + connector hint    PASS
legitimate conduit_token returned        PASS
final /f/conversation                    HTTP 422
GitHub tool evidence                     NOT REACHED
```

The combined test suite immediately before the final-submit run passed:

```text
30 passed in 0.17s
```

The final probe then returned:

```text
stage           conversation-submit
ok              false
blocked_status  BLOCKED_CAPABILITY
HTTP status     422
```

## Interpretation

HTTP 422 is not evidence that Sentinel/proof/Turnstile is required.

It is evidence that the final endpoint was reached but rejected the request at a validation/contract layer. The current experiment must therefore classify this boundary more precisely as:

```text
REQUEST_VALIDATION_REJECTED
```

while H2 overall remains `BLOCKED_CAPABILITY` because GitHub tool execution has not yet been materialized.

Do not attempt to bypass or fabricate product-security material based on this result.

## Comparison with the successful Web HAR

The current probe already sends the core GitHub activation structure:

```text
literal @GitHub
message-level system_hints
message serialization_metadata.custom_symbol_offsets
  symbol = ecosystemMention
top-level system_hints
client_prepare_state
timezone/timezone_offset_min
conversation_mode
enable_message_followups
supports_buffering
supported_encodings
legitimate X-Conduit-Token
```

The successful interactive HAR additionally contained body fields that the current probe does not yet reproduce:

```text
messages[0].create_time
model_response_contracts
client_contextual_info
paragen_cot_summary_display_override
force_parallel_switch
thinking_effort
local_function_names
```

The successful Web request also contained normal product/client and Sentinel-related headers. Their presence must not be interpreted as proof that they caused the 422 or that they must be reproduced by PowerPack.

The next step is to extract the safe validation error path from the 422 response before adding any of these fields.

## Safe 422 diagnostic

Use:

```bash
uv run python \
  scripts/homologation/diagnose_chatgpt_github_submit_422.py
```

The diagnostic repeats the same connector-aware final request but, on HTTP 422, reads the response only to emit a redacted validation summary.

Allowed output fields:

```text
type
loc
msg
```

Explicitly discarded/not emitted:

```text
input
request body
connector ids
plugin ids
conduit tokens
OAuth/session tokens
Authorization/Cookie values
Sentinel/proof values
raw backend diagnostics
```

If the backend reports a missing/invalid body field, add only the field proven necessary and rerun. If the request then reaches a 401/403 security boundary, record that separately and do not attempt to fabricate or bypass security material.

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
final conversation request validation     REJECTED (HTTP 422)
connector materialized in final turn      NOT PROVEN
GitHub tool-call evidence                 NOT REACHED
exact PR inspection                       NOT REACHED
production Web PR review                  BLOCKED_CAPABILITY
H2 overall                                BLOCKED_CAPABILITY
```
