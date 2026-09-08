# Experimental Web GitHub backend transport model

## Status

This document records an engineering hypothesis for evolving the browserless ChatGPT Project provider into a Web PR reviewer that can prove GitHub tool use.

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

A separate browserless experiment then demonstrated the boundary:

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

## Current evidence classification

The current browserless Web PR path should be described as:

```text
project_context_transport      PASS
project_binding                PASS
pr_identity_contract           PASS
plugin_installation_attested   PASS
repository_access_attested     PASS
@GitHub_mention_requested      PASS
github_tool_materialized       BLOCKED_CAPABILITY
exact_pr_tool_evidence         NOT_AVAILABLE
web_pr_review_overall          BLOCKED_CAPABILITY
```

This is not a user-configuration failure. The distinction matters because the same account/repository can expose GitHub successfully in an interactive ChatGPT product session while the browserless backend request does not.

## Working hypothesis

A richer GitHub-capable private-backend provider likely has at least two logical phases.

### Phase A — conversation/session capability initialization

Conceptually, the transport must create or resume a ChatGPT conversation in a state where:

- the selected ChatGPT account/workspace is known;
- the intended Project context is known where applicable;
- the GitHub app/plugin capability is eligible for use;
- the user instruction includes the canonical `@GitHub` invocation;
- the target repository/PR identity is explicit.

Candidate private-backend fields such as `plugin_ids`, `gizmo_id`, `conversation_mode`, parent/root message ids or conversation-tree metadata are hypotheses until captured and reproduced. Do not hard-code them from speculation.

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

The exact private SSE event names, message roles and execution-output structures are not yet contractual. Implementation must be based on captured evidence from the authenticated product flow, not guessed schemas.

## Authentication boundary

The current browserless provider intentionally uses Codex-derived ChatGPT authentication and does not copy browser cookies.

Existing proven material includes:

- bearer authentication derived from `~/.codex/auth.json`;
- ChatGPT account/workspace identity where required by the current backend path.

A browser `Cookie` header is **not currently an accepted PowerPack requirement** for GitHub tool execution. If experiments show that a GitHub-capable private conversation endpoint requires additional session material, the team must first answer:

1. Is the material obtainable from the already authenticated Codex/ChatGPT account without browser automation?
2. Can it be handled without persisting raw secrets in the repository or homologation evidence?
3. Does using it violate the browserless architecture or require a new provider mode?
4. How is logout/revocation handled?
5. What cross-platform behavior exists on WSL/Linux and Windows?

Only after those questions are resolved should the transport be implemented.

## Safe capture protocol for the next experiment

The next useful experiment is not another retry of `review run`. It is a structural comparison between:

```text
A. one ChatGPT Web/Desktop conversation where @GitHub actually opens the repository/PR
B. one PowerPack browserless request that returns BLOCKED_CAPABILITY
```

Capture only protocol structure. Do not copy credentials.

For the successful Web/Desktop session, record with secrets redacted:

```text
request order
request URL path or endpoint family
HTTP method
request body field names
which fields identify Project/GPT/plugin/app/conversation
which fields identify parent/root messages
which non-secret headers differ from PowerPack
SSE/event type names
presence and shape of tool-call events
presence and shape of tool-result events
final response event
```

For every request/response capture, redact completely:

```text
Authorization values
Cookie values
OAuth tokens
session tokens
CSRF tokens
signed URLs
raw account credentials
```

Safe placeholders are acceptable, for example:

```text
Authorization: <REDACTED>
Cookie: <REDACTED>
ChatGPT-Account-ID: <ACCOUNT-ID-PRESENT>
plugin_ids: [<ID-PRESENT>]
gizmo_id: <ID-PRESENT>
```

Do not send the raw HAR if it contains credentials. Prefer manually extracting a sanitized request skeleton or a redacted HAR copy.

## Required experiment evidence

Before replacing the current `/codex/responses` review transport, capture a successful ChatGPT Web/Desktop GitHub review and record, with secrets redacted:

```text
request sequence
endpoint family
HTTP method
non-secret headers
conversation/project identifiers and their semantics
request body field names and roles
SSE/event sequence
GitHub tool invocation evidence
GitHub tool result evidence
final assistant response
```

The experiment must include at least these negative controls:

```text
without @GitHub
with @GitHub
GitHub plugin disconnected
plugin connected but repository unauthorized
wrong PR repository
invalid PR number
```

These controls let PowerPack distinguish activation, capability, authorization and review-context failures.

## Decision rules for hypothesized fields

Do not promote any private field into production merely because it appears once.

A candidate field such as `plugin_ids`, `gizmo_id`, `conversation_mode`, a specific conversation endpoint, or an additional header becomes a PowerPack dependency only when:

1. it is present in a successful GitHub-enabled conversation;
2. removing or changing it reproduces loss of GitHub capability while the rest of the request remains equivalent;
3. its semantics can be expressed without embedding raw credentials into project configuration;
4. the behavior can be reproduced on the supported environment;
5. a fail-closed test covers upstream breakage.

Until then it remains an experiment observation, not an architecture contract.

## Provider acceptance contract

A future GitHub-capable Web provider is acceptable only when it can prove all of the following for the same immutable review snapshot:

```text
provider = chatgpt-project/web
Project binding resolved
GitHub plugin/app precondition attested
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

The implementation should preserve raw/redacted protocol evidence sufficient to debug upstream changes without leaking credentials.

## Why `@GitHub` alone is not sufficient evidence

The mention is a capability request, not proof of execution. This is now demonstrated by the current browserless experiment: the model received the mention and still returned `BLOCKED_CAPABILITY` because no GitHub tool was available.

A model could otherwise answer from Project memory, stale conversation context or prompt text. Therefore final Web PR homologation must require evidence that the exact PR was actually read through the GitHub capability.

## Re-homologation rule

Because the transport is built on non-public ChatGPT backend behavior, any change in endpoint shape, plugin activation, authentication, event format or tool availability invalidates the affected Web-provider homologation and requires a fresh H2/H4 run.
