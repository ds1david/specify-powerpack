# Browserless GitHub conversation probe status

## Purpose

This file records the current evidence for the browserless ChatGPT/GitHub transport experiments on `feat/homologation-harness`.

The transport uses the authenticated ChatGPT account derived from `~/.codex/auth.json`. It does not use Playwright, Chromium, copied browser cookies, hard-coded connector ids, or fabricated Sentinel/proof material.

## Proven on WSL

The following combined unit suite passed:

```text
26 passed in 0.17s
```

The read-only GitHub connector preflight had already proven:

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

The next probe was then executed successfully:

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

Therefore this boundary is now proven:

```text
Codex-derived ChatGPT auth
  -> dynamic GitHub connector discovery
  -> active connector authorization preflight
  -> POST /backend-api/conversation/init
       system_hints = [plugin:connector_<resolved-id>]
  -> successful response
```

## Important interpretation

This does **not** mean the production Web reviewer is connector-aware yet.

`review run --provider web` still uses the existing `/backend-api/codex/responses` path. A subsequent real PR #92 review still returned `BLOCKED_CAPABILITY`, which is expected until the connector-aware conversation transport is integrated into the provider.

Current separation:

```text
experimental probe transport
  conversation/init + connector hint        PASS

production Web review transport
  codex/responses + textual @GitHub          BLOCKED_CAPABILITY
```

Do not classify that blocked production review as a GitHub authorization failure.

## Next probe: conversation prepare

The next controlled stage is:

```text
POST /backend-api/f/conversation/prepare
```

using:

```text
model resolved from conversation/init
client-generated parent/root message id
conversation_mode.kind = primary_assistant
system_hints = [plugin:connector_<resolved-id>]
partial_query = GitHub ...
supports_buffering = true
```

The probe must only check whether the response contains a conduit token. The token value is transient secret/session material and must never be printed, logged, committed, or included in homologation evidence.

The prepare probe does **not** submit the final user message and does **not** invoke the GitHub tool.

Only after `prepare` succeeds legitimately should the experiment consider a final `/f/conversation` submission with:

```text
literal @GitHub
+ top-level connector system_hint
+ message-level connector system_hint
+ ecosystemMention serialization metadata
```

No experiment may fabricate Sentinel, proof-of-work, Turnstile, conduit, or other anti-abuse/session material.

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
conversation/prepare                      PENDING
connector materialized in final turn      PENDING
GitHub tool-call evidence                 PENDING
exact PR inspection                       PENDING
production Web PR review                  BLOCKED_CAPABILITY
H2 overall                                BLOCKED_CAPABILITY
```
