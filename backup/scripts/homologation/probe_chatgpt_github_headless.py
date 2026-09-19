#!/usr/bin/env python3
"""Linux/WSL GitHub connector probe against the real ChatGPT Web app.

This probe uses a persistent Chromium profile. The browser itself obtains
Sentinel, Turnstile and conduit material after a genuine Web login. The probe
never fabricates those values, never injects Codex OAuth as a Web session, and
never prints cookies, tokens or header values. It only submits after the Web
composer materializes the GitHub connector context.

Known WSL constraint: this account authenticates ChatGPT through Google. Google
rejects sign-in in Playwright Chromium (automation/testing browser). A headed
Chromium login loop is therefore not a viable path. Do not treat that failure as
a PowerPack API bug. Use Windows Chrome CDP or keep REST as the primary smoke.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_PROMPT = (
    "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM "
    "POWERPACK_GITHUB_TOOL_OK"
)
MARKER = "POWERPACK_GITHUB_TOOL_OK"
CHAT_URL = "https://chatgpt.com/"
CONNECTOR_RE = re.compile(r"^plugin:connector_[A-Za-z0-9_-]+$")
COMPOSER_SELECTOR = (
    '[role="textbox"]#prompt-textarea, [role="textbox"].ProseMirror, textarea#prompt-textarea'
)
LOGIN_SELECTOR = 'a[href*="/auth/login"], a[href*="/login"], button[data-testid*="login"]'


def checkpoint(name: str, **values: Any) -> None:
    safe = {key: value for key, value in values.items() if key not in {"token", "headers", "cookies", "body"}}
    print(json.dumps({"checkpoint": name, **safe}, ensure_ascii=False), file=sys.stderr, flush=True)


def default_profile() -> Path:
    return Path.home() / ".config" / "speckit-powerpack" / "browser-profiles" / "linux" / "headless-github"


def parse_json_body(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def has_connector(values: Any) -> bool:
    return any(isinstance(value, str) and CONNECTOR_RE.match(value) for value in (values or []))


def request_path(url: str) -> str:
    return url.split("?", 1)[0]


def header_presence(headers: Any, names: tuple[str, ...]) -> dict[str, bool]:
    available = {str(name).casefold() for name in (headers or {}).keys()}
    return {name: name.casefold() in available for name in names}


def session_blocked_report(
    *,
    status: int | None,
    cookies_present: bool,
    headed: bool,
    login_selector_visible: bool = False,
) -> dict[str, Any]:
    if status == 403:
        classification = "WEB_CHALLENGE_BLOCKED"
        error = (
            "ChatGPT Web returned HTTP 403 before the composer became available; "
            "the browser was stopped by the Web/Cloudflare challenge."
        )
    elif login_selector_visible:
        classification = "GOOGLE_IDP_REJECTS_CHROMIUM"
        error = (
            "ChatGPT Web reached a login surface, but this account authenticates via Google "
            "and Google does not allow sign-in in Playwright Chromium. "
            "Do not retry Chromium login; use Windows Chrome CDP or REST."
        )
    else:
        classification = "WEB_SESSION_REQUIRED"
        error = (
            "ChatGPT Web composer is unavailable; this WSL profile has no usable Web session. "
            "Google SSO into Playwright Chromium is not supported for this account."
        )
    return {
        "ok": False,
        "stage": "headless-github-flow",
        "classification": classification,
        "error": error,
        "evidence": {
            "navigation_http_status": status,
            "cookies_present": cookies_present,
            "login_selector_visible": login_selector_visible,
            "headed": headed,
            "codex_auth_injected": False,
            "codex_auth_is_not_web_session": True,
            "google_sso_rejected_on_chromium": True,
        },
        "raw_secrets_included": False,
    }


async def safe_close(browser) -> None:
    try:
        await browser.close()
    except Exception:
        return


async def wait_for_composer(page, timeout_s: float) -> bool:
    try:
        await page.wait_for_selector(COMPOSER_SELECTOR, timeout=timeout_s * 1000)
        return True
    except Exception:
        return False


async def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required. Install with: uv sync --extra browser && uv run playwright install chromium") from exc

    profile = Path(args.profile).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True)
    headed = bool(args.headed)
    checkpoint(
        "profile_ready",
        profile=str(profile),
        headless=not headed,
        url=args.url,
        extra_codex_headers=False,
        check_only=bool(args.check_only),
        wait_for_login=bool(args.wait_for_login),
    )

    context_change: dict[str, Any] | None = None
    final_request: dict[str, Any] | None = None
    final_status: int | None = None
    response_text_parts: list[str] = []
    request_ids: dict[str, str] = {}
    navigation_headers_logged = False
    sentinel_header_names = (
        "openai-sentinel-chat-requirements-token",
        "openai-sentinel-proof-token",
        "openai-sentinel-turnstile-token",
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch_persistent_context(
            str(profile),
            headless=not headed,
            locale=args.locale,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        checkpoint(
            "browser_started",
            header_names_injected=[],
            values_logged=False,
            cookies_loaded=bool(await browser.cookies()),
            headed=headed,
        )

        async def on_request(request) -> None:
            nonlocal context_change, final_request, navigation_headers_logged
            if not navigation_headers_logged and request.resource_type == "document" and "chatgpt.com" in request.url:
                navigation_headers_logged = True
                checkpoint(
                    "navigation_request_headers",
                    header_presence=header_presence(request.headers, ("authorization", "chatgpt-account-id")),
                    header_names_logged=True,
                    values_logged=False,
                )
            if request.method != "POST":
                return
            path = request_path(request.url)
            if path.endswith("/f/conversation/prepare"):
                body = parse_json_body(request.post_data)
                if not body or body.get("client_prepare_source") != "context_change":
                    return
                partial = ""
                try:
                    partial = str(body["partial_query"]["content"]["parts"][0])
                except (KeyError, IndexError, TypeError):
                    pass
                candidate = {
                    "observed": True,
                    "connector_hint_present": has_connector(body.get("system_hints")),
                    "partial_query_starts_with_github": partial.casefold().startswith("github"),
                    "client_prepare_state": body.get("client_prepare_state"),
                }
                if candidate["connector_hint_present"] and candidate["partial_query_starts_with_github"]:
                    context_change = candidate
                    checkpoint("github_connector_materialized", **candidate)
                return
            if path.endswith("/f/conversation"):
                body = parse_json_body(request.post_data)
                if not body:
                    return
                metadata = ((body.get("messages") or [{}])[0].get("metadata") or {})
                serialization = metadata.get("serialization_metadata") or {}
                offsets = serialization.get("custom_symbol_offsets") or []
                final_request = {
                    "observed": True,
                    "top_level_connector_hint": has_connector(body.get("system_hints")),
                    "message_connector_hint": has_connector(metadata.get("system_hints")),
                    "ecosystem_mention_present": any(item.get("symbol") == "ecosystemMention" for item in offsets if isinstance(item, dict)),
                    "sentinel_headers_present": all(header_presence(request.headers, sentinel_header_names).values()),
                    "sentinel_header_presence": header_presence(request.headers, sentinel_header_names),
                }
                request_ids["final"] = request.headers.get("x-request-id", "")
                checkpoint("final_submit_observed", **{key: value for key, value in final_request.items() if key != "observed"})

        async def on_response(response) -> None:
            nonlocal final_status
            if request_path(response.url).endswith("/f/conversation") and response.request.method == "POST":
                final_status = response.status
                checkpoint("final_submit_response", http_status=final_status)

        page.on("request", on_request)
        page.on("response", on_response)
        checkpoint("navigate", url=args.url)
        navigation = await page.goto(args.url, wait_until="domcontentloaded")
        login_visible = await page.locator(LOGIN_SELECTOR).count() > 0
        page_title = await page.title()
        status = navigation.status if navigation else None
        checkpoint(
            "navigation_result",
            final_url=page.url,
            title=page_title,
            http_status=status,
            login_selector_visible=login_visible,
            cookie_count=len(await browser.cookies()),
        )
        composer_ready = await wait_for_composer(page, args.page_timeout)
        if not composer_ready and args.wait_for_login:
            checkpoint(
                "waiting_for_genuine_login",
                timeout_s=args.login_timeout,
                google_sso_rejected_on_chromium=True,
            )
            composer_ready = await wait_for_composer(page, args.login_timeout)
        if not composer_ready:
            cookies_present = bool(await browser.cookies())
            await safe_close(browser)
            return session_blocked_report(
                status=status,
                cookies_present=cookies_present,
                headed=headed,
                login_selector_visible=login_visible,
            )
        checkpoint("composer_ready")

        if args.check_only:
            await safe_close(browser)
            return {
                "ok": True,
                "stage": "headless-github-flow",
                "classification": "COMPOSER_READY",
                "send_clicked": False,
                "evidence": {
                    "composer_ready": True,
                    "headed": headed,
                    "codex_auth_injected": False,
                    "github_context_change_prepare": False,
                    "final_submit_observed": False,
                },
                "raw_secrets_included": False,
            }

        composer = page.locator(COMPOSER_SELECTOR).first
        await composer.click()
        await composer.fill(args.prompt)
        checkpoint("prompt_inserted", prompt_starts_with_github=args.prompt.lstrip().casefold().startswith("@github"))

        deadline = time.monotonic() + args.mention_timeout
        while context_change is None and time.monotonic() < deadline:
            await page.wait_for_timeout(250)
        if context_change is None:
            await safe_close(browser)
            return {
                "ok": False,
                "stage": "headless-github-flow",
                "classification": "GITHUB_CONNECTOR_NOT_MATERIALIZED",
                "send_clicked": False,
                "raw_secrets_included": False,
            }

        send = page.locator('button[data-testid="send-button"], button[aria-label*="Send" i], form button[type="submit"]').last
        await send.click()
        checkpoint("send_clicked")
        try:
            await page.wait_for_selector('[data-message-author-role="assistant"]', timeout=args.response_timeout * 1000)
            await page.wait_for_timeout(1000)
        except Exception:
            pass
        assistants = page.locator('[data-message-author-role="assistant"]')
        if await assistants.count():
            response_text_parts.append((await assistants.last.inner_text()).strip())
        await safe_close(browser)

    response_text = "\n".join(part for part in response_text_parts if part).strip()
    accepted = bool(
        final_request
        and final_status == 200
        and final_request.get("top_level_connector_hint")
        and final_request.get("message_connector_hint")
        and final_request.get("ecosystem_mention_present")
        and final_request.get("sentinel_headers_present")
        and MARKER in response_text
    )
    return {
        "ok": accepted,
        "stage": "headless-github-flow",
        "classification": "HEADLESS_GITHUB_FLOW_ACCEPTED" if accepted else "HEADLESS_GITHUB_FLOW_INCOMPLETE",
        "request": {
            "transport": "playwright-chromium-headed" if headed else "playwright-chromium-headless",
            "send_guarded_by_connector_materialization": True,
            "sentinel_headers_logged": False,
            "codex_auth_injected": False,
        },
        "evidence": {
            "github_context_change_prepare": context_change is not None,
            "final_submit_observed": final_request is not None,
            "final_http_status": final_status,
            "sentinel_headers_present": bool(final_request and final_request.get("sentinel_headers_present")),
            "marker_seen": MARKER in response_text,
            "assistant_response_complete": bool(response_text),
        },
        "assistant_text": response_text if args.include_assistant_text else None,
        "raw_secrets_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Linux/WSL ChatGPT Web GitHub connector smoke")
    parser.add_argument("--url", default=CHAT_URL)
    parser.add_argument("--profile", type=Path, default=default_profile())
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--locale", default="pt-BR")
    parser.add_argument("--headed", action="store_true", help="Open a visible Chromium window")
    parser.add_argument("--check-only", action="store_true", help="Stop after the composer is reachable")
    parser.add_argument(
        "--wait-for-login",
        action="store_true",
        help="Wait for composer after login. Google SSO into Playwright Chromium is not supported for this account.",
    )
    parser.add_argument("--mention-timeout", type=float, default=30)
    parser.add_argument("--page-timeout", type=float, default=30)
    parser.add_argument("--login-timeout", type=float, default=300)
    parser.add_argument("--response-timeout", type=float, default=240)
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()
    try:
        report = asyncio.run(run(args))
    except Exception as exc:
        report = {"ok": False, "stage": "headless-github-flow", "classification": "BLOCKED_CONFIGURATION", "error": str(exc), "raw_secrets_included": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
