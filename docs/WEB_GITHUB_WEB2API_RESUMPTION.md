# Resuming ChatGPT-Web2API for GitHub-enabled Web review

## Decision

After the browserless `/backend-api/f/conversation` experiments crossed from HTTP 422 body validation to a repeatable HTTP 403 product/security boundary, the GitHub-enabled review turn returns to the existing ChatGPT-Web2API/Chrome transport.

The browserless work is not discarded. Its Codex-authenticated account/Project/connector discovery remains useful as a preflight. The actual mutation/send is delegated to the real ChatGPT Web frontend through the pinned Web2API CDP driver.

## Historical finding: Web2API was not removed by one later commit

The repository history has two lines that diverged before PR #5 was merged.

The Web2API line was built on September 6, 2026 through commits including:

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

`main` currently contains PR #5 at:

```text
65846fbfb7e40bff7c8b37252aae5b84b8946697
```

The browserless/homologation line descends from the earlier merge base:

```text
520b0ea599cc1fa9a59058debcc5416511e2c51b
```

and later evolved around:

```text
~/.codex/auth.json
  -> ChatGPTBackendClient
  -> Project discovery/binding
  -> GitHub connector discovery
  -> direct conversation experiments
```

Therefore the correct interpretation is not "Web2API was removed." The two implementations evolved in parallel and the browserless feature branch never inherited the later PR #5 merge.

## Authentication clarification

Two authentication contexts are intentionally kept separate.

### Codex-authenticated preflight

PowerPack reads:

```text
~/.codex/auth.json
```

through `ChatGPTBackendClient` and verifies that the authenticated ChatGPT account can resolve the GitHub connector.

This proves account/backend capability before opening the browser path.

### Web2API review turn

ChatGPT-Web2API uses a real headed Chrome profile and the normal ChatGPT Web session in that profile.

PowerPack does **not**:

```text
copy the Codex bearer token into Chrome
convert ~/.codex/auth.json into cookies
copy browser cookies into WSL
fabricate Sentinel/proof/Turnstile values
replay product security material from HAR captures
```

The browser frontend produces its own legitimate session/security/turn orchestration.

## Why Web2API is the appropriate send boundary

The pinned upstream is:

```text
repository: Octo-Lex/ChatGPT-Web2API
revision:   497527dceabfa3f95961e23c291e618c5570f1ac
```

The upstream itself previously established that direct `/backend-api/f/conversation` sends hit an HTTP 403 gate, including experiments with browser-like TLS. Its supported write path therefore drives the real browser DOM through CDP.

The PowerPack browserless reproduction independently reached the same architectural boundary after matching the successful HAR's non-secret turn semantics:

```text
old direct reproduction     -> 422 Invalid conversation body
corrected direct reproduction -> 403 SECURITY_OR_RATE_BOUNDARY
```

That evidence is consistent with delegating mutation/send to the real frontend rather than cloning the private protocol.

## GitHub-enabled send seam

The pinned Web2API `CDPDriver.send_and_stream()` already owns the critical turn lifecycle:

```text
assistant-count baseline
-> IdentityListener health/capture scope
-> turn anchor
-> type_message(text)
-> click_send()
-> send acknowledgment
-> completion detection
-> conversation-id discovery
-> anchored backend reconciliation
```

PowerPack does not replace this sequence.

The GitHub capability is inserted at one narrow seam:

```text
send_and_stream(review_prompt)
    |
    +-- Web2API type_message("@GitHub ...")
    |
    +-- POWERPACK GATE:
    |      wait for native ChatGPT frontend to emit
    |      POST /backend-api/f/conversation/prepare
    |        client_prepare_source = context_change
    |        system_hints contains plugin:connector_*
    |        partial_query starts "GitHub ..."
    |
    |      if not observed -> fail closed; click_send is never reached
    |
    +-- return from type_message wrapper
    |
    +-- Web2API click_send()
    |
    +-- native frontend submit
    |
    +-- Web2API completion/reconciliation
```

This matters because the successful complete HAR showed that the frontend resolved the pasted `@GitHub` mention **before** the user clicked Send.

## Final-submit evidence

The observer chains Web2API's existing `IdentityListener` instead of replacing it.

For the native final request it records only booleans/enums:

```text
top-level plugin:connector_* present
message-level plugin:connector_* present
ecosystemMention present
client_prepare_state
HTTP response status
```

It never persists:

```text
connector id value
Authorization
Cookie
OAuth/session token
conduit token
Sentinel/proof/Turnstile token
CSRF material
raw POST headers
```

Success for the generic capability probe requires:

```text
Codex-auth GitHub connector preflight             PASS
Web2API CDPDriver connected                       PASS
GitHub context_change observed before Send        PASS
connector hint before Send                        PASS
native final submit observed                      PASS
final top-level connector hint                     PASS
final message connector hint                       PASS
final ecosystemMention                             PASS
final /f/conversation HTTP 200                     PASS
completed assistant response                       PASS
POWERPACK_GITHUB_TOOL_OK marker                     PASS
```

## Files

```text
scripts/homologation/probe_chatgpt_github_web2api.py
scripts/homologation/probe_chatgpt_github_web2api.ps1
scripts/homologation/web2api_github_driver_probe.py
tests/test_chatgpt_github_web2api_probe_contract.py
```

The earlier direct-CDP probe remains diagnostic evidence only. It is not the resumed product architecture.

## Runtime topology on WSL + Windows

```text
WSL PowerPack probe
  |
  +-- ~/.codex/auth.json
  |     -> ChatGPTBackendClient
  |     -> dynamic GitHub connector preflight
  |
  +-- powershell.exe
        -> dedicated Windows venv
        -> pinned ChatGPT-Web2API
        -> Web2API service owns persistent headed Chrome profile
        -> helper uses the same pinned Web2API package
        -> CDPDriver owned tab
        -> real ChatGPT frontend
        -> GitHub context-change gate
        -> native Send
        -> Web2API response reconciliation
```

Default probe resources are isolated from the historical PR #5 defaults:

```text
REST port: 8097
CDP port:  9231
profile:   %LOCALAPPDATA%\SpecKitPowerPack\reviewers\web2api-github-probe
```

## First-run login

The Windows lifecycle launcher creates a persistent Web2API reviewer profile. If ChatGPT is not authenticated, the headed Chrome window is the place where the human completes normal login/MFA.

No credentials are entered into PowerPack.

After the profile is authenticated, subsequent probe runs reuse that browser profile.

## Current scope

This probe proves the transport/capability boundary only. It does not by itself approve H2.

H2 still requires a later run against the bound Project and exact PR review contract:

```text
Project identity
+ exact repository/PR identity
+ GitHub tool materialization
+ actual PR inspection
+ immutable review evidence
+ final verdict on the intended snapshot
```
