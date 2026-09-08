# ChatGPT Web GitHub HAR findings

## Capture scope

Two Microsoft Edge HAR captures now cover complementary parts of the ChatGPT Web GitHub flow:

1. selecting **Plugins → GitHub → Use in chat** while GitHub is already installed/authenticated; and
2. successfully sending:

```text
@GitHub LISTE TDOS OS MEUS REPOSITORIOS
```

This document contains only redacted structural findings. Raw HAR files may contain sensitive session material and must not be committed.

## Primary finding

The successful Web flow did not rely on the literal `@GitHub` text alone.

ChatGPT represented the selected GitHub app as a connector hint using the shape:

```text
plugin:connector_<github-connector-id>
```

The connector identifier observed in the HAR matched the GitHub connector available through the authenticated ChatGPT plugin environment used during the investigation.

## Plugin discovery and selection

The second HAR captured the UI path **Plugins → GitHub → Use in chat** before a message was sent. It establishes how the Web client resolves the GitHub plugin/app into the connector identifier later injected into a conversation.

### 1. Installed plugin catalog

```http
GET /backend-api/ps/plugins/installed?limit=1000
```

The GitHub record had this structural relationship:

```text
plugin id:          plugin_connector_1p_<redacted>
name/display name:  github / GitHub
canonical_app_id:   connector_<github-connector-id>
connector_id:       connector_<github-connector-id>
release.app_ids:    [connector_<github-connector-id>]
status:              ENABLED
enabled:             true
authentication:      ON_INSTALL
```

This is currently the strongest candidate for **dynamic GitHub connector discovery**. PowerPack should not hard-code a connector id when the authenticated account can resolve it from the installed-plugin catalog.

### 2. Specific plugin detail

After the GitHub plugin was selected, the Web client requested:

```http
GET /backend-api/ps/plugins/plugin_connector_1p_<redacted>
```

The response repeated the mapping:

```text
plugin_connector_1p_<redacted>
  -> canonical_app_id = connector_<github-connector-id>
  -> connector_id     = connector_<github-connector-id>
  -> release.app_ids  = [connector_<github-connector-id>]
```

For the captured GitHub plugin, the release was an OpenAI-provided Developer Tools plugin with interactive/write capability metadata. Those descriptive fields are useful for validation but are not part of the minimum connector identity contract.

### 3. App metadata

The client then requested app metadata:

```http
POST /backend-api/apps/content?detail=full&platform=chat&locale=<locale>
```

with a body equivalent to:

```json
{
  "app_ids": [
    "connector_<github-connector-id>"
  ]
}
```

The response identified the app as GitHub, status `ENABLED`, connector type `SERVICE`, and OAuth-capable.

### 4. Accessible account links

The client queried:

```http
POST /backend-api/aip/connectors/links/list_accessible
```

The captured response contained a GitHub link associated with the same connector id and reported an active OAuth authorization state. Sensitive user/account/link identifiers are intentionally omitted here.

This provides a stronger preflight signal than the user attestation flag alone: a future experimental provider can check that the authenticated ChatGPT account has an active accessible GitHub link without reading or persisting OAuth credentials.

### 5. Connector/app availability

The client also queried:

```http
GET /backend-api/aip/connectors/connector_<github-connector-id>/siwc
POST /backend-api/apps/availability?platform=chat&locale=<locale>
```

The app-availability response for GitHub reported the connector as installed, available and enabled.

The `/siwc` response is recorded as an observation only. Its exact semantics are not yet understood and it must not become a PowerPack requirement without an ablation test.

### 6. What “Use in chat” did not do

Because GitHub was already installed and authenticated, the captured **Use in chat** interaction did not show an installation mutation, OAuth exchange or new connector creation. The relevant traffic was discovery/detail/availability state.

The best current interpretation is:

```text
installed plugin catalog
  -> resolve plugin_connector_1p_<id>
  -> resolve canonical connector_<github-id>
  -> verify app metadata
  -> verify accessible OAuth link
  -> verify app availability
  -> composer can reference connector_<github-id>
```

The later conversation HAR proves how that resolved connector id is actually attached to the turn.

## Request sequence for a GitHub-enabled conversation

### 1. Conversation initialization

```http
POST /backend-api/conversation/init
```

Relevant request body shape:

```json
{
  "requested_default_model": null,
  "conversation_id": null,
  "timezone": "<timezone>",
  "timezone_offset_min": "<offset>",
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

The prepare response included a conduit token. The token value is session material and must never be logged or committed.

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

The Edge HAR preserved multiple Server-Sent Events with event names including:

```text
delta_encoding
message
delta
```

The exporter did not preserve the SSE event payload bodies. Therefore this HAR proves a streamed multi-event conversation but does **not** yet expose the exact GitHub tool-call or tool-result message shapes.

A future capture should use a method that preserves SSE data while redacting secrets.

## Surrounding turn orchestration

The conversation HAR also contained normal ChatGPT turn infrastructure including:

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

The HAR captures exposed some non-secret header names, including ChatGPT account/session metadata, but sensitive authentication values are not suitable evidence.

Do not infer that browser cookies are mandatory from these captures. Likewise, do not infer that cookies are unnecessary merely because a HAR exporter omitted them. Authentication requirements must be established through controlled browserless requests using the already supported Codex-derived ChatGPT authentication.

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
plugins/installed
  -> GitHub plugin_connector_1p_<id>
  -> canonical connector_<github-id>
apps/content + accessible links + availability
  -> connector installed/authenticated/available
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

Priority discovery and transport pieces now supported by HAR evidence:

```text
1. GET /backend-api/ps/plugins/installed
   -> resolve GitHub plugin record
   -> canonical_app_id / connector_id
2. optionally GET /backend-api/ps/plugins/<plugin-id> to confirm mapping
3. POST /backend-api/apps/content for connector metadata
4. POST /backend-api/aip/connectors/links/list_accessible for active authorization state
5. POST /backend-api/apps/availability for installed/available/enabled state
6. /backend-api/f/conversation transport
7. connector system_hints
8. message metadata.system_hints
9. ecosystemMention custom_symbol_offsets
10. /conversation/init connector hint
11. /f/conversation/prepare and conduit lifecycle
```

`plugin_ids`, `gizmo_id`, browser cookies and exact tool-event schemas are now lower-priority/unproven for this observed path.

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
