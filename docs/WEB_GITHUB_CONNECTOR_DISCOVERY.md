# ChatGPT Web GitHub connector discovery

## Status

This document records redacted structural evidence from an Edge HAR captured while selecting **Plugins → GitHub → Use in chat** in ChatGPT Web, plus the browserless reproduction executed on WSL with Codex-derived ChatGPT authentication.

It documents a private ChatGPT product flow, not a public or stable API contract. Raw HAR files must not be committed because they may contain sensitive session information.

## Main result

PowerPack does not need to hard-code a GitHub connector id. The authenticated ChatGPT account can resolve the GitHub plugin and its canonical connector dynamically through the same catalog endpoints observed in the Web product.

Observed relationship:

```text
GitHub plugin
  plugin id:        plugin_connector_1p_<redacted>
  canonical_app_id: connector_<github-id>
  connector_id:     connector_<github-id>
  release.app_ids:  [connector_<github-id>]
```

The later conversation HAR uses that canonical connector as:

```text
plugin:connector_<github-id>
```

## Browserless WSL proof

The read-only probe was executed successfully on WSL using the existing `~/.codex/auth.json` path through `ChatGPTBackendClient` and without Playwright, Chromium, browser-cookie copying or hard-coded connector ids.

Command:

```bash
uv run python \
  scripts/homologation/probe_chatgpt_github_connector.py \
  --locale pt-BR
```

Observed result:

```text
ok                                      true
GitHub plugin resolved                  true
GitHub plugin status                    ENABLED
GitHub plugin enabled                   true
authentication_policy                   ON_INSTALL
GitHub connector resolved               true
connector metadata status               ENABLED
connector type                          SERVICE
accessible GitHub link                  true
auth_type                               OAUTH
auth_status                             ACTIVE
visibility                              VISIBLE
connector_status                        ENABLED
apps_privacy_control                    full_access
availability found                      true
installed                               true
available                               true
can_install                             false
availability status                     ENABLED
raw_secrets_included                    false
```

The same checkout also passed the combined harness/context/HAR/probe unit suite:

```text
24 passed in 0.21s
```

Therefore the browserless GitHub connector discovery and authorization preflight is now **PROVEN PASS on WSL for the homologated account/environment**. This is not yet proof that the connector can be materialized inside a browserless conversation turn.

## Discovery sequence

### Installed plugins

```http
GET /backend-api/ps/plugins/installed?limit=1000
```

Find the unique enabled plugin whose name/display name resolves to GitHub.

Minimum fields observed:

```text
id
name
canonical_app_id
connector_id
status
enabled
authentication_policy
release.display_name
release.app_ids
```

For the homologated account:

```text
name = github
release.display_name = GitHub
status = ENABLED
enabled = true
authentication_policy = ON_INSTALL
```

Do not persist the plugin id or connector id as a universal constant. Resolve them per authenticated account/product state.

### Plugin detail confirmation

```http
GET /backend-api/ps/plugins/plugin_connector_1p_<redacted>
```

The detail response repeats the canonical connector mapping. The browserless probe requires the detail response to confirm the same connector id.

### App content

```http
POST /backend-api/apps/content?detail=full&platform=chat&locale=<locale>
```

Request shape:

```json
{
  "app_ids": ["connector_<github-id>"]
}
```

Observed GitHub app properties include:

```text
name = GitHub
status = ENABLED
connector_type = SERVICE
supported_auth includes OAUTH
```

### Accessible connector links

```http
POST /backend-api/aip/connectors/links/list_accessible
```

The browserless probe resolved an accessible GitHub link for the same connector with:

```text
auth_type = OAUTH
auth_status = ACTIVE
visibility = VISIBLE
connector_status = ENABLED
connector_type = SERVICE
apps_privacy_control = full_access
```

This is now proven as a browserless preflight for an already connected GitHub account. PowerPack must never log or persist link/account identifiers or OAuth credential material from this response.

### Availability

```http
POST /backend-api/apps/availability?platform=chat&locale=<locale>
```

Request shape:

```json
{
  "app_ids": ["connector_<github-id>"]
}
```

The browserless probe confirmed:

```text
installed = true
available = true
can_install = false
status = ENABLED
```

### Additional connector probe

The Web client also called:

```http
GET /backend-api/aip/connectors/connector_<github-id>/siwc
```

The response has fields such as `available` and `has_grant`, but its semantics are not yet understood. It remains observation-only and is not required by the proven preflight.

## “Use in chat” interpretation

The HAR did not show a new plugin installation, connector creation or OAuth authorization exchange when **Use in chat** was clicked. GitHub was already installed and authenticated.

The evidence supports this interpretation:

```text
open plugin catalog
  -> resolve GitHub plugin record
  -> resolve canonical connector id
  -> inspect connector/app metadata
  -> confirm accessible authorization link
  -> confirm app availability
  -> composer records selected connector locally
  -> later conversation turn injects plugin:connector_<id>
```

The actual conversation HAR independently shows the final connector injection through `system_hints` and `ecosystemMention` metadata.

## Proven browserless preflight contract

The preflight can now be treated as an implemented/proven capability on the WSL homologation target:

```text
1. GET installed plugins
2. resolve exactly one GitHub plugin
3. derive exactly one canonical connector id
4. fetch plugin detail and require the same connector id
5. query app content and require GitHub + ENABLED + SERVICE
6. query accessible links and require an ACTIVE OAuth GitHub link
7. query app availability and require installed + available + ENABLED
8. emit only redacted evidence
```

Fail-closed classification:

```text
no GitHub plugin in installed catalog
  -> BLOCKED_CONFIGURATION or BLOCKED_CAPABILITY depending on product availability evidence

GitHub plugin found but no active accessible link
  -> BLOCKED_CONFIGURATION

GitHub connector found and link active but app unavailable
  -> BLOCKED_CAPABILITY

preflight passes but conversation still lacks GitHub tool
  -> BLOCKED_CAPABILITY (transport/materialization)
```

The last case is the current H2 boundary.

## Security constraints

The discovery implementation may retain only non-secret state needed for the current run. It must not emit or persist:

```text
Authorization values
Cookie values
OAuth tokens
session tokens
raw connector-link identifiers tied to a user
raw account identifiers
signed asset URLs
```

Connector/plugin ids used transiently to assemble the current request may be kept in memory and must be redacted in homologation evidence.

## Next experiment

Connector discovery is no longer the open question. The next controlled experiment is conversation capability materialization using the dynamically resolved connector.

Priority sequence:

```text
conversation/init
  + plugin:connector_<resolved-id> system_hint

then, only if init succeeds legitimately:

f/conversation/prepare
  + same connector hint
  + normal root/parent message identity

then, only if prepare succeeds legitimately without fabricating security material:

f/conversation
  + literal @GitHub
  + top-level system_hint
  + message-level system_hint
  + ecosystemMention metadata
```

Do not fabricate Sentinel/proof/conduit material. Values returned legitimately by the backend may be used transiently and must never be logged. If the private conversation transport requires product-only anti-abuse orchestration that cannot be obtained through the existing authenticated flow, record that as `BLOCKED_CAPABILITY`/architectural boundary rather than attempting to bypass it.
