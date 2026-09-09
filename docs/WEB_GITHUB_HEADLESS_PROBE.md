# Linux/WSL ChatGPT Web headless/headed probe

## Purpose

`scripts/homologation/probe_chatgpt_github_headless.py` checks whether a **genuine**
ChatGPT Web session in a persistent Linux/WSL Chromium profile can reach the
composer, materialize the GitHub connector, and complete a native Send.

It is a secondary authentic-Web validation layer. It is not the product smoke
path. The primary functional smoke remains REST via `/backend-api/codex/responses`.

## What this probe must not do

- Inject Codex OAuth (`Authorization: Bearer …`) as if it were a ChatGPT Web session
- Copy cookies, HAR headers, Sentinel, Turnstile or proof values
- Print tokens, cookies or header values
- Treat cookie presence or a logged-in-looking document as a usable composer

Codex device auth and the Playwright Web profile are different runtimes. See
`docs/CHATGPT_WEB_ACCOUNTS.md`.

## Google SSO blocks Playwright Chromium

This ChatGPT account authenticates through Google. Google does not allow sign-in
in Playwright Chromium. A headed Linux/WSL Chromium window therefore cannot
complete a genuine Web session for this account.

That is an identity-provider/browser restriction, not a PowerPack API bug.
Do not retry Chromium login, copy cookies, or inject Codex tokens as a workaround.

Viable alternatives:

- Primary product path: REST `/backend-api/codex/responses`
- Authentic Web path, if needed: Windows Chrome CDP (`docs/WEB_GITHUB_CDP_PROBE.md`),
  because Google SSO works in real Chrome, not in Playwright Chromium

## Commands

Check whether the composer is reachable, without sending:

```bash
uv sync --extra browser
uv run playwright install chromium
uv run python scripts/homologation/probe_chatgpt_github_headless.py \
  --headed --check-only \
  --profile ~/.config/speckit-powerpack/browser-profiles/linux/ds1david
```

`--wait-for-login` is retained for non-Google accounts. It is not a viable
bootstrap for this workspace: Google will reject Chromium sign-in.

Only after `COMPOSER_READY`, rerun without `--check-only` to test GitHub
connector materialization and native submit. That state is not expected from
Playwright Chromium while Google SSO remains the account login method.

## Classification

| Result | Meaning |
| --- | --- |
| `COMPOSER_READY` | Genuine Web UI reached the composer. Session is usable enough to continue. |
| `WEB_CHALLENGE_BLOCKED` | HTTP 403 / Cloudflare challenge before the composer. Not an API bug in PowerPack. |
| `WEB_SESSION_REQUIRED` | No usable Web session in this profile. |
| `GOOGLE_IDP_REJECTS_CHROMIUM` | Login UI appeared, but Google SSO cannot complete in Playwright Chromium. |
| `GITHUB_CONNECTOR_NOT_MATERIALIZED` | Composer worked, but `@GitHub` did not become connector context. Send was not clicked. |
| `HEADLESS_GITHUB_FLOW_ACCEPTED` | Native submit 200 with connector metadata and the response marker. |

## Product direction

For this account, WSL Playwright Chromium cannot obtain a genuine Web session
because Google blocks login in Chromium. Keep REST as the primary transport.
If authentic Web submit must be proven, use Windows Chrome CDP
(`docs/WEB_GITHUB_CDP_PROBE.md`). Do not reconstruct `/f/conversation`
security material.
