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

For GitHub-enabled ChatGPT sessions, the operational workflow additionally requires:

```text
GitHub app/plugin installed and connected
  -> target repository authorized
  -> explicit @GitHub invocation
  -> exact PR inspection
```

OpenAI publicly documents connecting GitHub to ChatGPT, authorizing repositories, and explicitly invoking connected apps/plugins with `@` mentions. It does not document the private backend payloads used internally to materialize a GitHub-capable conversation.

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

Do **not** record bearer tokens, OAuth tokens, cookies or other raw credential values.

The experiment must also include negative controls:

```text
without @GitHub
with @GitHub
GitHub plugin disconnected
plugin connected but repository unauthorized
wrong PR repository
invalid PR number
```

These controls let PowerPack distinguish activation, capability, authorization and review-context failures.

## Provider acceptance contract

A future GitHub-capable Web provider is acceptable only when it can prove all of the following for the same immutable review snapshot:

```text
provider = chatgpt-project/web
Project binding resolved
GitHub plugin/app precondition attested
canonical @GitHub invocation emitted
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

The mention is a capability request, not proof of execution. A model could still answer from Project memory, stale conversation context or prompt text.

Therefore final Web PR homologation must eventually require evidence that the exact PR was actually read through the GitHub capability. Until that evidence is available, the provider may prove Project context and activation behavior, but it must not claim full PR-review homologation.

## Re-homologation rule

Because the transport is built on non-public ChatGPT backend behavior, any change in endpoint shape, plugin activation, authentication, event format or tool availability invalidates the affected Web-provider homologation and requires a fresh H2/H4 run.
