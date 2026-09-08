# Web2API-only GitHub prompt probe

## Decision

The GitHub prompt capability probe is now intentionally isolated to the existing ChatGPT-Web2API/Chrome transport.

It does not use:

```text
~/.codex/auth.json
ChatGPTBackendClient
browserless connector discovery
direct /backend-api/f/conversation submit
the earlier direct-CDP probe
```

The purpose of this probe is narrow: prove whether the real ChatGPT Web frontend, driven through the pinned ChatGPT-Web2API implementation, can materialize `@GitHub` in the composer before Send and complete a GitHub-enabled turn.

## Historical context

The repository has two lines that evolved in parallel:

```text
main / PR #5
  -> ChatGPT-Web2API
  -> Chrome/CDP
  -> real frontend

feat/homologation-harness browserless experiments
  -> ~/.codex/auth.json
  -> direct backend-api reads/conversation probes
```

The Web2API line was built through commits including:

```text
a7a5f3c  feat(review): add ChatGPT Web2API backend adapter
d689ac9  feat(review): wire reviewer identities and Projects to Web2API
2f2b779  refactor(review): make Web2API the functional reviewer backend
e7bfe33  docs(review): route Web gate through ChatGPT-Web2API
d6a8ce1  config(review): make Web2API the versioned Web gate policy
3e9b4a5  fix(review): install Web2API from pinned GitHub revision
69f68c8  fix(review): fail closed on degraded Web2API transport
65846fb  Merge PR #5: functional ChatGPT Project reviewer bridge
```

The pinned upstream remains:

```text
repository: Octo-Lex/ChatGPT-Web2API
revision:   497527dceabfa3f95961e23c291e618c5570f1ac
```

## Runtime topology

```text
WSL probe
  |
  +-- powershell.exe
        |
        +-- dedicated Windows venv
        |
        +-- pinned ChatGPT-Web2API service
        |     |
        |     +-- owns persistent headed Chrome profile
        |     +-- owns Chrome/CDP lifecycle
        |
        +-- Web2API helper executed by the same venv
              |
              +-- chatgpt_web2api.CDPDriver
              +-- owned ChatGPT tab
              +-- navigate_new_chat(project optional)
              +-- send_and_stream(prompt)
```

No Codex bearer token is read or passed anywhere in this flow.

## GitHub enablement gate

The pinned Web2API `CDPDriver.send_and_stream()` already owns the native turn lifecycle:

```text
assistant-count baseline
-> IdentityListener
-> turn anchor
-> type_message(text)
-> click_send()
-> acknowledgment
-> completion detector
-> conversation-id discovery
-> anchored reconciliation
```

The PowerPack probe changes only the seam between `type_message()` and `click_send()`.

```text
send_and_stream("@GitHub ...")
    |
    +-- Web2API type_message("@GitHub ...")
    |
    +-- POWERPACK GATE
    |      wait for native frontend:
    |
    |      POST /backend-api/f/conversation/prepare
    |      client_prepare_source = context_change
    |      system_hints contains plugin:connector_*
    |      partial_query starts with "GitHub "
    |
    |      not observed -> fail closed
    |                     Send is not clicked
    |
    +-- gate succeeds
    |
    +-- return to Web2API send_and_stream
    |
    +-- Web2API click_send()
    |
    +-- native ChatGPT frontend submit
    |
    +-- Web2API completion/reconciliation
```

This follows the successful interactive HAR behavior: `@GitHub` is resolved into structured connector state before the final Send.

## Network evidence

The helper chains the Web2API `IdentityListener` rather than replacing it.

It records only non-secret evidence:

```text
GitHub context_change observed
connector hint present before Send
partial_query starts with GitHub
final /f/conversation request observed
top-level connector hint present
message-level connector hint present
ecosystemMention present
client_prepare_state
final HTTP status
assistant response completed
POWERPACK_GITHUB_TOOL_OK marker present
```

It does not persist:

```text
Authorization
Cookie
connector id value
OAuth/session tokens
conduit token
Sentinel/proof/Turnstile values
CSRF material
raw request headers
```

## Generic capability PASS

The generic prompt is:

```text
@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK
```

`WEB2API_GITHUB_FLOW_ACCEPTED` requires all of these:

```text
Web2API CDPDriver connected                    PASS
GitHub context_change before Send             PASS
connector hint before Send                    PASS
final native submit observed                  PASS
top-level connector hint                      PASS
message-level connector hint                  PASS
ecosystemMention                              PASS
/f/conversation HTTP 200                      PASS
assistant response completed                  PASS
POWERPACK_GITHUB_TOOL_OK                       PASS
```

If the GitHub context is not materialized before Send, the classification is:

```text
WEB2API_GITHUB_MENTION_NOT_RESOLVED
```

and the probe explicitly does not reach Web2API's `click_send()`.

## Files

```text
scripts/homologation/probe_chatgpt_github_web2api.py
scripts/homologation/probe_chatgpt_github_web2api.ps1
scripts/homologation/web2api_github_driver_probe.py
tests/test_chatgpt_github_web2api_probe_contract.py
```

## Default isolated resources

```text
REST port: 8097
CDP port:  9231
profile:   %LOCALAPPDATA%\SpecKitPowerPack\reviewers\web2api-github-probe
```

The profile is persistent. On first execution the user may need to complete normal ChatGPT login/MFA in the headed Chrome window.

## Scope

This probe is a transport/capability test only. It does not by itself approve H2.

After this generic prompt passes, the next step is the Project + exact PR review flow:

```text
bound Project
+ exact repository/PR identity
+ GitHub connector materialization
+ actual PR inspection
+ immutable review evidence
+ final verdict on the intended snapshot
```
