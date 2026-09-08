# Browserless GitHub conversation probe status

## Purpose

This file records the current evidence for the browserless ChatGPT/GitHub transport experiments on `feat/homologation-harness`.

The transport uses the authenticated ChatGPT account derived from `~/.codex/auth.json`. It does not use Playwright, Chromium, copied browser cookies, hard-coded connector ids, or fabricated Sentinel/proof material.

## Proven on WSL

The following combined unit suite passed:

```text
28 passed in 0.17s
```

The read-only GitHub connector preflight has proven:

```text
GitHub plugin dynamically resolved          PASS
GitHub connector dynamically resolved       PASS
connector metadata ENABLED                  PASS
connector type SERVICE                      PASS
OAuth accessible link present               PASS
OAuth auth_status ACTIVE                    PASS
connector_status ENABLED                    PASS
apps_privacy_control full_access             PASS
app installed                               PASS
app available                               PASS
```

### Conversation init

The connector-aware initialization probe succeeded:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_conversation_init.py
```

Observed redacted result:

```text
stage                                    conversation-init
ok                                       true
POST /backend-api/conversation/init      PASS
connector system_hint present            true
user prompt sent                         false
GitHub tool invoked                      false
response received                        true
default model metadata returned          true
raw secrets included                     false
```

### Conversation prepare

The connector-aware prepare probe also succeeded:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_conversation_prepare.py
```

Observed redacted result:

```text
stage                                    conversation-prepare
ok                                       true
POST /backend-api/f/conversation/prepare PASS
connector system_hint present            true
conversation_mode.kind                    primary_assistant
model resolved from init                 true
parent/root message id generated         true
partial query sent                       true
final user message sent                  false
GitHub tool invoked                      false
prepare response received                true
prepare response keys                    conduit_token, status
conduit token present                    true
conduit token exposed                    false
raw secrets included                     false
```

Therefore this boundary is now proven:

```text
Codex-derived ChatGPT auth
  -> dynamic GitHub connector discovery
  -> active connector authorization preflight
  -> POST /backend-api/conversation/init
       system_hints = [plugin:connector_<resolved-id>]
  -> successful response + default model
  -> POST /backend-api/f/conversation/prepare
       same connector hint
       generated root/parent message id
       partial GitHub query
  -> successful response + legitimate conduit_token
```

## Important interpretation

This does **not** mean the production Web reviewer is connector-aware yet.

`review run --provider web` still uses the existing `/backend-api/codex/responses` path. A subsequent real PR #92 review still returned `BLOCKED_CAPABILITY`, which is expected until the connector-aware conversation transport is integrated into the provider.

Current separation:

```text
experimental probe transport
  connector discovery                         PASS
  conversation/init + connector hint           PASS
  conversation/prepare + legitimate conduit    PASS

production Web review transport
  codex/responses + textual @GitHub             BLOCKED_CAPABILITY
```

Do not classify that blocked production review as a GitHub authorization failure.

## Next probe: final conversation submission

The next controlled stage is:

```text
POST /backend-api/f/conversation
```

The probe may use only material already obtained legitimately from the authenticated flow:

```text
literal @GitHub
+ dynamically resolved plugin:connector_<id>
+ top-level connector system_hint
+ message-level connector system_hint
+ ecosystemMention serialization metadata
+ model from conversation/init
+ parent/root message id used in prepare
+ conduit token returned by prepare
```

The Edge HAR showed that the interactive product also sends Sentinel/proof/Turnstile-related headers on the final request. The browserless probe must **not** fabricate, derive, bypass, or replay those security values. It intentionally omits them.

The final-submit probe therefore has two acceptable outcomes:

```text
1. backend accepts the request without fabricated security material
   -> inspect SSE structurally for real GitHub tool evidence

2. backend rejects the request because product turn-security material is required
   -> BLOCKED_CAPABILITY
   -> record the architectural boundary
   -> do not attempt to bypass the protection
```

A textual answer mentioning GitHub is not sufficient proof. Full success requires structural GitHub tool evidence in the streamed events plus the expected completion marker.

Probe:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_conversation_submit.py
```

The probe never prints the connector id, conduit token, OAuth credentials, Sentinel/proof values, or raw backend security diagnostics.

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
connector materialized in final turn      PENDING
GitHub tool-call evidence                 PENDING
exact PR inspection                       PENDING
production Web PR review                  BLOCKED_CAPABILITY
H2 overall                                BLOCKED_CAPABILITY
```
