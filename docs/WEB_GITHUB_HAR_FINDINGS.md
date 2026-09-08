# ChatGPT Web GitHub HAR findings

## Capture scope

A Microsoft Edge HAR was captured while a ChatGPT Web conversation successfully invoked the connected GitHub app with:

```text
@GitHub LISTE TDOS OS MEUS REPOSITORIOS
```

This document contains only redacted structural findings. The raw HAR may contain sensitive session material and must not be committed.

## Primary finding

The successful Web flow did not rely on the literal `@GitHub` text alone.

ChatGPT represented the selected GitHub app as a connector hint using the shape:

```text
plugin:connector_<github-connector-id>
```

The connector identifier observed in the HAR matched the GitHub connector available through the authenticated ChatGPT plugin environment used during the investigation.

## Request sequence

### 1. Conversation initialization

```http
POST /backend-api/conversation/init
```

Relevant request body shape:

```json
{
  "requested_default_model": null,
  "conversation_id": null,
  "timezone": "America/Sao_Paulo",
  "timezone_offset_min": 180,
  "conversation_origin": null,
  "system_hints": [
    "plugin:connector_<github-connector-id>"
  ]
}
```

The response returned ordinary conversation metadata and the selected default model.

### 2. Conversation preparation

```http
POST /backend-api/f/conversation/prepare
```

Relevant request shape:

```json
{
  "action": "next",
  "parent_message_id": "client-created-root",
  "model": "<model-slug>",
  "conversation_mode": {
    "kind": "primary_assistant"
  },
  "system_hints": [
    "plugin:connector_<github-connector-id>"
  ],
  "partial_query": {
    "author": {
      "role": "user"
    },
    "content": {
      "content_type": "text",
      "parts": [
        "GitHub LISTE TDOS OS MEUS REPOSITORIOS"
      ]
    }
  },
  "supports_buffering": true
}
```

The prepare response included a conduit token. The token value is credential/session material and must never be logged or committed.

A second prepare call was observed later during composer state change, retaining the same connector `system_hints`.

### 3. Conversation submission

```http
POST /backend-api/f/conversation
Accept: text/event-stream
```

Relevant request shape:

```json
{
  "action": "next",
  "messages": [
    {
      "author": {
        "role": "user"
      },
      "content": {
        "content_type": "text",
        "parts": [
          "@GitHub LISTE TDOS OS MEUS REPOSITORIOS"
        ]
      },
      "metadata": {
        "system_hints": [
          "plugin:connector_<github-connector-id>"
        ],
        "serialization_metadata": {
          "custom_symbol_offsets": [
            {
              "id": "plugin:connector_<github-connector-id>",
              "symbol": "ecosystemMention",
              "startIndex": 0,
              "endIndex": 7
            }
          ]
        },
        "submission_mode": "manual_send"
      }
    }
  ],
  "parent_message_id": "client-created-root",
  "model": "<model-slug>",
  "conversation_mode": {
    "kind": "primary_assistant"
  },
  "system_hints": [
    "plugin:connector_<github-connector-id>"
  ],
  "supports_buffering": true
}
```

This is the strongest evidence currently available for GitHub capability materialization in the Web product.

## `gizmo_id` / `plugin_ids` finding

The successful final conversation payload did **not** include:

```text
plugin_ids
gizmo_id
```

The resulting conversation metadata also reported:

```text
gizmo_id: null
```

For this capture, GitHub therefore behaved as a connected app/connector rather than a Custom GPT selected through `gizmo_id`.

This does not prove those fields are never used by other ChatGPT surfaces. It proves they were not required by this observed successful flow.

## Streaming evidence

The final conversation endpoint returned:

```text
Content-Type: text/event-stream
```

The Edge HAR preserved 32 Server-Sent Events with event names including:

```text
delta_encoding
message
delta
```

The exporter did not preserve the SSE event payload bodies. Therefore this HAR proves a streamed multi-event conversation but does **not** yet expose the exact GitHub tool-call or tool-result message shapes.

A future capture should use a method that preserves SSE data while redacting secrets.

## Surrounding turn orchestration

The HAR also contained normal ChatGPT turn infrastructure including:

```text
/backend-api/sentinel/chat-requirements/prepare
/backend-api/sentinel/chat-requirements/finalize
/backend-api/sentinel/ping
/backend-api/conversation/<id>/stream_status
```

The final conversation request carried conduit and sentinel-related headers.

These fields must not be copied blindly into PowerPack. The HAR does not establish whether they are GitHub-specific, generic ChatGPT anti-abuse/turn orchestration, or mandatory for a legitimate browserless client.

PowerPack must not fabricate or bypass sentinel/proof mechanisms.

## Authentication-header observation

The exported HAR did not expose header names for:

```text
Authorization
Cookie
ChatGPT-Account-ID
```

on the successful conversation requests.

This is inconclusive because browser HAR exports may omit sensitive authentication headers. Do not infer either that cookies are mandatory or that they are unnecessary from this capture alone.

## Comparison with current PowerPack transport

Current PowerPack Web provider:

```text
POST /backend-api/codex/responses
model/input/instructions/reasoning
literal @GitHub mention
no connector system_hint
no ecosystemMention metadata
```

Observed successful Web product flow:

```text
conversation/init
  + connector system_hint
prepare
  + connector system_hint
conversation submit
  + connector system_hint
  + message-level connector system_hint
  + ecosystemMention metadata
  + literal @GitHub
```

This comparison strongly explains the observed result:

```text
PowerPack /codex/responses + @GitHub
  -> BLOCKED_CAPABILITY

Interactive ChatGPT connector-aware conversation
  -> GitHub capability available
```

## Implementation direction

Do not jump directly to a full browser-clone transport. Reproduce capability activation with controlled ablation experiments.

Priority fields/endpoints to investigate:

```text
1. /backend-api/f/conversation transport
2. connector system_hints
3. message metadata.system_hints
4. ecosystemMention custom_symbol_offsets
5. /conversation/init connector hint
6. /f/conversation/prepare and conduit lifecycle
```

`plugin_ids`, `gizmo_id`, browser cookies and exact tool-event schemas remain secondary/unproven for this path.

## Security rules

Never commit or publish the raw HAR.

Never preserve values for:

```text
Authorization
Cookie
OAuth/session tokens
conduit tokens
sentinel/proof tokens
CSRF material
signed URLs
raw account credentials
```

Only redacted structural evidence is suitable for PowerPack documentation and homologation artifacts.
