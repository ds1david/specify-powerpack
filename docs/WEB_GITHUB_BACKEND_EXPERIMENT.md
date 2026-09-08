# Experimental Web GitHub backend transport model

## Status

This document records the evidence and engineering hypothesis for evolving the browserless ChatGPT Project provider into a Web PR reviewer that can prove GitHub tool use.

It is **not** a claim about a public or stable OpenAI API. The current provider uses non-public ChatGPT backend paths and must fail closed when upstream behavior changes.

## What is already established

The current PowerPack browserless path has independently demonstrated:

```text
Codex-authenticated ChatGPT account
  -> Project discovery
  -> interactive Project selection
  -> persisted repository-to-Project binding
  -> Project metadata/conversation context
  -> ChatGPT backend response
```

The interactive ChatGPT Web/Desktop product flow has also demonstrated that, when the GitHub app/plugin is already installed/authenticated and the repository is authorized, an explicit `@GitHub` mention can expose repository access in that product session.

A separate browserless experiment demonstrated the boundary:

```text
same ChatGPT account
+ valid Project binding
+ GitHub app/plugin already installed/authenticated
+ target repository authorized
+ effective prompt starts with @GitHub
+ current chatgpt.com/backend-api/codex/responses transport
= BLOCKED_CAPABILITY
```

Therefore an `@GitHub` string in the prompt is not sufficient to materialize the GitHub tool in the current `codex/responses` transport.

## HAR observation: successful interactive GitHub activation

A Microsoft Edge HAR was captured from a successful interactive ChatGPT conversation using the prompt:

```text
@GitHub LISTE TDOS OS MEUS REPOSITORIOS
```

The raw HAR is sensitive evidence and must not be committed. Only redacted structural findings belong in the repository.

The capture materially changes the transport hypothesis. The successful interactive flow did **not** show `plugin_ids` or `gizmo_id` in the submitted conversation payload. Instead, GitHub was represented as an app/connector through a connector hint.

Observed request sequence:

```text
POST /backend-api/conversation/init
  system_hints: ["plugin:connector_<github-connector-id>"]

POST /backend-api/f/conversation/prepare
  system_hints: ["plugin:connector_<github-connector-id>"]
  partial_query: "GitHub LISTE TDOS OS MEUS REPOSITORIOS"
  -> returns conduit token

POST /backend-api/f/conversation/prepare
  same connector system_hint during composer state change

POST /backend-api/f/conversation
  messages[0].content.parts[0]: "@GitHub LISTE TDOS OS MEUS REPOSITORIOS"
  messages[0].metadata.system_hints:
    ["plugin:connector_<github-connector-id>"]
  messages[0].metadata.serialization_metadata.custom_symbol_offsets[0]:
    id: "plugin:connector_<github-connector-id>"
    symbol: "ecosystemMention"
    startIndex: 0
    endIndex: 7
  top-level system_hints:
    ["plugin:connector_<github-connector-id>"]
  response: text/event-stream
```

The connector identifier captured in the HAR matched the GitHub connector exposed by the authenticated ChatGPT plugin environment used during this investigation. This is strong evidence that the connector hint, not merely the literal `@GitHub` text, participates in capability materialization.

The submitted conversation was a normal primary-assistant conversation and the resulting conversation metadata had `gizmo_id = null`. For this observed flow, GitHub therefore behaved as a connected app/connector rather than as a Custom GPT selected through a `gizmo_id`.

### Important negative finding

The captured successful request did **not** contain `plugin_ids` or `gizmo_id` in the final `POST /backend-api/f/conversation` payload.

Those fields remain possible in other ChatGPT surfaces, but they are no longer the primary implementation hypothesis for this PowerPack path.

### Conversation plumbing observed in the HAR

The successful flow also used surrounding ChatGPT conversation plumbing:

```text
POST /backend-api/conversation/init
POST /backend-api/f/conversation/prepare
POST /backend-api/sentinel/chat-requirements/prepare
POST /backend-api/sentinel/chat-requirements/finalize
POST /backend-api/f/conversation
GET  /backend-api/conversation/<id>/stream_status
```

The final conversation request carried a conduit token and sentinel-related request headers. These appear to be part of normal ChatGPT turn orchestration, but the HAR alone does not prove which of them are GitHub-specific or mandatory for a browserless reproduction.

The HAR exporter preserved SSE event names (`message`, `delta`, `delta_encoding`) but did not preserve the event payload data needed to reconstruct the exact tool-call/tool-result messages. A second capture method is still required for tool-loop evidence.

## Authentication evidence from the HAR

The exported HAR does not contain request header names for `Authorization`, `Cookie`, or `ChatGPT-Account-ID` on the successful conversation requests.

This must **not** be interpreted as proof that those headers were absent on the wire. Browser HAR exports may omit sensitive authentication material. The only safe conclusion is:

```text
HAR does not prove browser cookies are required.
HAR does not prove browser cookies are unnecessary.
```

The current browserless provider must continue to avoid browser-cookie copying unless a controlled experiment proves additional session material is necessary and the security/architecture decision is reviewed explicitly.

## Current evidence classification

The current browserless Web PR path should be described as:

```text
project_context_transport      PASS
project_binding                PASS
pr_identity_contract           PASS
plugin_installation_attested   PASS
repository_access_attested     PASS
@GitHub_mention_requested      PASS
connector_hint_injected        NOT_IMPLEMENTED
github_tool_materialized       BLOCKED_CAPABILITY
exact_pr_tool_evidence         NOT_AVAILABLE
web_pr_review_overall          BLOCKED_CAPABILITY
```

This is not a user-configuration failure. The same account/repository can expose GitHub successfully in an interactive ChatGPT product session while the current browserless backend request does not.

## Revised working hypothesis

A richer GitHub-capable private-backend provider likely has at least two logical phases.

### Phase A — conversation/session capability initialization

The highest-priority reproduction candidate is now:

```text
conversation/init
  + connector system_hint
  -> conversation/prepare
       + same connector system_hint
       -> conversation send
            + literal @GitHub mention
            + message-level connector system_hint
            + top-level connector system_hint
            + ecosystemMention serialization metadata
```

The transport must create or resume a ChatGPT conversation in a state where:

- the selected ChatGPT account/workspace is known;
- the intended Project context is known where applicable;
- the GitHub app/connector capability is eligible for use;
- the GitHub connector identifier is resolved dynamically, never hard-coded;
- the user instruction includes the canonical `@GitHub` invocation;
- the mention is represented using the connector metadata expected by the product flow;
- the target repository/PR identity is explicit.

`plugin_ids`, `gizmo_id` and other candidate fields are secondary hypotheses unless a later capture proves they are used by the relevant product surface.

### Phase B — tool-call lifecycle and final answer

A complete provider must not assume that the first streamed assistant text is the final answer. Conceptually it must support a loop equivalent to:

```text
assistant requests GitHub operation
  -> authenticated GitHub capability executes server-side
  -> repository/PR evidence returns to the conversation
  -> model continues reasoning
  -> zero or more additional GitHub operations
  -> final reviewer answer
```

The exact private SSE payload shape is still unproven because the Edge HAR preserved only event names, not event data. Implementation must be based on captured evidence from the authenticated product flow, not guessed schemas.

## Authentication boundary

The current browserless provider intentionally uses Codex-derived ChatGPT authentication and does not copy browser cookies.

Existing proven material includes:

- bearer authentication derived from `~/.codex/auth.json` for the current PowerPack backend path;
- ChatGPT account/workspace identity where required by that path.

A browser `Cookie` header is **not currently an accepted PowerPack requirement** for GitHub tool execution. If experiments show that a GitHub-capable private conversation endpoint requires additional session material, the team must first answer:

1. Is the material obtainable from the already authenticated Codex/ChatGPT account without browser automation?
2. Can it be handled without persisting raw secrets in the repository or homologation evidence?
3. Does using it violate the browserless architecture or require a new provider mode?
4. How is logout/revocation handled?
5. What cross-platform behavior exists on WSL/Linux and Windows?

Only after those questions are resolved should the transport be implemented.

## Next controlled experiment

The next experiment should reproduce the successful interactive request structure incrementally rather than guessing the entire Web client protocol at once.

Recommended ablation order:

```text
E0 current /codex/responses baseline
   -> expected BLOCKED_CAPABILITY

E1 /f/conversation with literal @GitHub only
   -> establish conversation transport baseline

E2 E1 + top-level system_hints connector

E3 E2 + message metadata.system_hints connector

E4 E3 + serialization_metadata.custom_symbol_offsets ecosystemMention

E5 E4 + /conversation/init connector hint

E6 E5 + /f/conversation/prepare connector hint + conduit token
```

At each stage, preserve only redacted structural evidence and require a concrete GitHub operation such as listing repositories. The first stage that materializes GitHub capability identifies the minimal contract more safely than copying every browser field.

Do not attempt to reproduce sentinel or other anti-abuse/security headers by fabrication. If the private endpoint rejects a legitimate Codex-authenticated request because product-only turn orchestration is required, record that as an architectural boundary rather than bypassing platform protections.

## Safe capture protocol

For any future successful Web/Desktop capture, record only:

```text
request order
request URL path or endpoint family
HTTP method
request body field names
which fields identify Project/app/connector/conversation
which fields identify parent/root messages
which non-secret headers differ from PowerPack
SSE/event type names
presence and shape of tool-call events
presence and shape of tool-result events
final response event
```

Redact completely:

```text
Authorization values
Cookie values
OAuth tokens
session tokens
CSRF tokens
sentinel/proof token values
conduit token values
signed URLs
raw account credentials
```

Do not commit raw HAR files.

## Required experiment evidence

Before replacing the current `/codex/responses` review transport, a successful browserless experiment must record, with secrets redacted:

```text
request sequence
endpoint family
HTTP method
non-secret headers
conversation/project identifiers and their semantics
connector identifier discovery source
request body field names and roles
SSE/event sequence
GitHub tool invocation evidence
GitHub tool result evidence
final assistant response
```

The experiment must include at least these negative controls:

```text
without @GitHub
with @GitHub text only
connector hint without mention metadata
GitHub plugin disconnected
plugin connected but repository unauthorized
wrong PR repository
invalid PR number
```

These controls let PowerPack distinguish mention rendering, connector activation, capability, authorization and review-context failures.

## Decision rules for private fields

Do not promote any private field into production merely because it appears once.

A candidate field such as `system_hints`, `serialization_metadata.custom_symbol_offsets`, `conversation_mode`, a specific conversation endpoint, a conduit token, or an additional header becomes a PowerPack dependency only when:

1. it is present in a successful GitHub-enabled conversation;
2. removing or changing it reproduces loss of GitHub capability while the rest of the request remains equivalent;
3. its value can be resolved dynamically rather than hard-coded to one account/session;
4. its semantics can be expressed without embedding raw credentials into project configuration;
5. the behavior can be reproduced on the supported environment;
6. a fail-closed test covers upstream breakage.

Until then it remains experiment evidence, not an architecture contract.

## Provider acceptance contract

A future GitHub-capable Web provider is acceptable only when it can prove all of the following for the same immutable review snapshot:

```text
provider = chatgpt-project/web
Project binding resolved
GitHub app/connector precondition attested
GitHub connector dynamically resolved
canonical @GitHub invocation emitted
actual GitHub capability materialized
exact repository resolved
exact PR resolved
base ref/base SHA captured
head ref/head SHA captured
changed-file evidence observed through GitHub capability
reviewer response completed after tool-use
BLOCKED_* detected as non-success
```

The implementation should preserve redacted protocol evidence sufficient to debug upstream changes without leaking credentials.

## Why `@GitHub` alone is not sufficient evidence

The mention is a capability request, not proof of execution. This is demonstrated by the current browserless experiment: the model received the mention and still returned `BLOCKED_CAPABILITY` because no GitHub tool was available.

The successful HAR additionally shows that the Web product represents the GitHub mention structurally with connector hints and `ecosystemMention` metadata. That is the current strongest explanation for why plain mention text in `/codex/responses` is insufficient.

## Re-homologation rule

Because the transport is built on non-public ChatGPT backend behavior, any change in endpoint shape, connector activation, authentication, event format or tool availability invalidates the affected Web-provider homologation and requires a fresh H2/H4 run.
