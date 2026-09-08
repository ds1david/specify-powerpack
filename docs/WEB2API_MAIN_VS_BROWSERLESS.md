# Web2API main path vs browserless provider experiments

## Purpose

SpecKit PowerPack currently has two distinct ChatGPT Web review lines that must not be conflated.

### `main` — PR #5 Web2API/CDP bridge

The current `main` baseline is commit `65846fbfb7e40bff7c8b37252aae5b84b8946697`, merged from PR #5. It contains the functional ChatGPT-Web2API bridge with a dedicated headed Chrome/CDP session and the pinned upstream `Octo-Lex/ChatGPT-Web2API` revision `497527dceabfa3f95961e23c291e618c5570f1ac`.

Conceptually:

```text
PowerPack
  -> local ChatGPT-Web2API proxy
  -> dedicated Chrome/CDP profile
  -> real ChatGPT Web frontend
  -> private backend/Sentinel/tool orchestration executed by the product frontend
```

This path is browser-driven and must be preserved as the PR #5 baseline until a replacement is independently proven and integrated. Do not revert PR #5 merely because the browserless experiments exist.

### `feat/homologation-harness` — browserless candidate

The homologation/browserless branch intentionally does not contain the `chatgpt_web2api_*` runtime. Its current direction is:

```text
~/.codex/auth.json
  -> ChatGPTBackendClient
  -> Project discovery/binding
  -> GitHub plugin/connector discovery
  -> connector-aware conversation experiments
```

The browserless path has already proven Project access and read-only GitHub connector discovery/authorization without Playwright, Chromium, persistent browser profiles, copied cookies or hard-coded connector ids.

It has not yet proven GitHub tool materialization inside a browserless conversation turn. Until that is proven, Web PR review remains fail-closed as `BLOCKED_CAPABILITY`.

## What the Web2API analysis contributes

The Web2API/CDP path is useful as a behavioral reference because the real ChatGPT frontend performs private conversation orchestration, plugin selection and security challenges on the user's behalf.

However, implementation details from Web2API must not be copied blindly into the browserless provider. In particular:

```text
Web2API/CDP evidence
  -> useful for understanding product behavior
  -> useful for HAR/protocol comparison
  -> NOT proof that browser automation is required
  -> NOT justification for reintroducing Playwright/Chromium/cookie copying
```

The browserless experiments should continue to reproduce only the minimum legitimate backend contract that can be exercised with Codex-derived ChatGPT authentication and normal server-issued values.

## GitHub plugin distinction

The Web2API path currently sends ordinary text into the composer through CDP. Merely inserting `@GitHub` as text is not sufficient proof that the GitHub app/connector is structurally selected.

Independent HAR evidence from the interactive ChatGPT product shows that a selected GitHub app is represented with:

```text
plugin:connector_<github-id> system_hints
+ @GitHub ecosystemMention metadata
+ connector-aware conversation initialization/submission
```

The browserless provider therefore uses HAR-derived connector discovery and conversation-ablation experiments rather than assuming that text insertion is equivalent to tool activation.

## Confirmed main-path issues

Two issues identified while reviewing the current `main` Web2API adapter are confirmed and tracked separately from the browserless provider.

### Issue #7 — wrong conversation identifier

PowerPack currently assigns:

```python
conversation_id=str(value.get("id")) if value.get("id") else None
```

The pinned ChatGPT-Web2API response contains two distinct fields:

```text
id               = chatcmpl-...
conversation_id  = real ChatGPT conversation UUID
```

The adapter should use `conversation_id` for ChatGPT conversation identity/evidence and must not treat the OpenAI-compatible `chatcmpl-*` response id as the ChatGPT conversation id.

Tracked as GitHub issue #7.

### Issue #8 — optional Web2API proxy API-key support

The pinned ChatGPT-Web2API service can optionally protect its local REST API with configured API keys. The current PowerPack client has no user-scoped configuration path for that key and its native urllib request only sets `Content-Type` on JSON requests.

If this protection is used, PowerPack needs an optional Bearer credential path that remains outside the worktree/versioned configuration and is always redacted from evidence.

Tracked as GitHub issue #8.

These are bugs/capabilities of the PR #5 Web2API path. They must not be incorrectly copied into the browserless provider, whose authentication model is the Codex-derived ChatGPT account rather than a local proxy API key.

## Public API / MCP alternative

A public OpenAI API + GitHub MCP integration is architecturally separate from the PowerPack requirement to reuse a user's ChatGPT Project/account context.

It can be considered as a future provider because it offers a public tool contract, but it must not silently replace the ChatGPT subscription/Project provider. Such a provider would require separate OpenAI API and GitHub/MCP credentials and different cost/auth semantics.

Provider choice should therefore remain explicit:

```text
ChatGPT Project provider
  -> subscription/account context
  -> private/non-stable ChatGPT product backend
  -> fail closed on product drift

Public OpenAI API + GitHub MCP provider
  -> public API contract
  -> separate API credentials/billing
  -> separate provider capability
```

## Integration rule

When the browserless provider is eventually integrated with the PR #5 baseline:

1. preserve PR #5 behavior until replacement gates pass;
2. classify PR #5 Web2API defects separately from new browserless capability work;
3. do not restore browser automation into the browserless protocol layer;
4. retain provider-independent review invariants: exact PR identity, immutable snapshot, evidence, fail-closed provider readiness, and same-snapshot verdict;
5. require fresh H1/H2 homologation after integration.
