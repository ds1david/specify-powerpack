# Browserless GitHub final-submit 403 boundary

## Proven WSL evidence

After correcting the browserless final-turn sequence to match the complete successful ChatGPT Web HAR semantics, the final submit changed from HTTP 422 to HTTP 403.

Observed candidate commit before the small partial-query helper fix:

```text
6e88d13eebb63b9bba16a8c4f81748b7c71520be
```

Observed unit suite:

```text
1 failed, 47 passed
```

The single failure was a harness expectation that exposed an implementation bug in `_without_github_at()`: the complete successful HAR shows that the connector-resolution `partial_query` removes only the `@` sigil and preserves the literal `GitHub` token. The implementation removed the whole `@GitHub` token. This helper bug is fixed separately; it does not invalidate the HTTP 403 boundary because the final request still crossed the prior HTTP 422 validation layer.

Observed browserless probe result:

```text
stage           complete-har-flow
classification  SECURITY_OR_RATE_BOUNDARY
HTTP status     403
```

The request included the non-secret semantics observed in the successful Web turn:

```text
initial unresolved @GitHub prepare
connector context-change prepare
client_prepare_state = success on final submit
conversation_origin = tpp
model = gpt-5.6-sol-wm
thinking_effort = xhigh
connector system_hint
ecosystemMention metadata
legitimate conduit token
```

The probe deliberately did not send:

```text
browser cookies
Sentinel/proof/Turnstile values
product-only session/security headers
```

## Interpretation

This result materially narrows the architecture boundary:

```text
old browserless reproduction
  -> HTTP 422 Invalid conversation body

complete-HAR semantic reproduction
  -> HTTP 403
```

Therefore the prior body-validation failure is no longer the active blocker. The request reached a later authorization/security/product-turn gate.

HTTP 403 does not prove which individual product header or security mechanism is mandatory. The successful Web request contains browser-generated product/session and Sentinel-related headers, but PowerPack must not fabricate, replay, or bypass them.

The correct fail-closed classification remains:

```text
browserless final submit             BLOCKED_CAPABILITY
body/turn semantic parity            substantially proven
GitHub connector materialization     not proven browserless
GitHub tool-call evidence             not reached browserless
H2 browserless Web PR review          BLOCKED_CAPABILITY
```

## Product direction

This boundary strengthens the case for the existing Chrome/CDP Web2API transport for GitHub-enabled Web review:

```text
PowerPack
  -> ChatGPT-Web2API
  -> real Chrome + CDP
  -> insert @GitHub prompt into the real composer
  -> wait for the ChatGPT frontend to resolve the ecosystem mention
  -> verify the connector-aware context-change prepare
  -> click Send
  -> let the real frontend produce conduit/Sentinel/proof/session orchestration
  -> capture request/evidence with CDP Network events
  -> read the completed assistant response
```

The browserless transport remains valuable for Project context and connector discovery/preflight, but it should not attempt to bypass the product security boundary.
