# ChatGPT Web GitHub connector discovery

## Status

This document records redacted structural evidence from an Edge HAR captured while selecting **Plugins → GitHub → Use in chat** in ChatGPT Web.

It documents a private ChatGPT product flow, not a public or stable API contract. Raw HAR files must not be committed because they may contain sensitive session information.

## Main result

PowerPack does not need to hard-code a GitHub connector id if the authenticated ChatGPT account can access the same plugin catalog endpoints observed in the Web product.

The installed-plugin catalog already maps the human-facing GitHub plugin to the canonical connector used later in conversation `system_hints`.

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

For the captured account:

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

The detail response repeats the canonical connector mapping. This can be used as a confirmation step but may not be necessary if the installed-plugin response is sufficient and unambiguous.

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

Observed GitHub app properties included:

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

The captured response included an accessible GitHub link for the same connector with:

```text
auth_type = OAUTH
auth_status = ACTIVE
visibility = VISIBLE
connector_status = ENABLED
connector_type = SERVICE
apps_privacy_control = full_access
```

This is promising as a browserless preflight for an already connected GitHub account because it reports authorization state without exposing OAuth credential values.

PowerPack must never log or persist link/account identifiers or OAuth token material from this response.

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

The captured GitHub response reported:

```text
installed = true
available = true
status = ENABLED
```

### Additional connector probe

The Web client also called:

```http
GET /backend-api/aip/connectors/connector_<github-id>/siwc
```

The response has fields such as `available` and `has_grant`, but its semantics are not yet understood. It is observation-only and must not become a provider requirement until controlled ablation establishes its role.

## “Use in chat” interpretation

The HAR did not show a new plugin installation, connector creation or OAuth authorization exchange when **Use in chat** was clicked. GitHub was already installed and authenticated.

The current evidence therefore supports this interpretation:

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

## Proposed browserless preflight

Before experimenting with connector-aware `/f/conversation`, PowerPack can test whether the existing Codex-derived ChatGPT authentication is sufficient to perform the read-only discovery flow:

```text
1. GET installed plugins
2. resolve exactly one GitHub plugin
3. derive canonical connector id
4. optionally fetch plugin detail and require same connector id
5. query app content
6. query accessible links and require active GitHub link
7. query app availability and require installed + available + enabled
```

Failure classification should remain fail-closed:

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

The exact classification should be finalized only after the browserless read-only probe is executed against real accounts.

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

Connector/plugin ids used transiently to assemble the current request may be kept in memory and redacted in homologation evidence.

## Next experiment

The next useful experiment is **not** another plain `@GitHub` review. It is a browserless read-only connector discovery probe using the same Codex-derived ChatGPT auth already used by `ChatGPTBackendClient`.

The probe should answer:

```text
Can ~/.codex/auth.json + ChatGPT account identity call:
  /backend-api/ps/plugins/installed ?
  /backend-api/apps/content ?
  /backend-api/aip/connectors/links/list_accessible ?
  /backend-api/apps/availability ?
```

If yes, PowerPack can dynamically resolve and validate the GitHub connector without browser automation or hard-coded ids. Only then should the conversation-transport ablation proceed.
