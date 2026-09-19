from __future__ import annotations

from pathlib import Path
from typing import Any

from .chatgpt_project_provider import ChatGPTBackendClient, load_codex_auth


def _codex_compatible_headers(self: ChatGPTBackendClient, *, accept: str = "application/json") -> dict[str, str]:
    """Headers used by Codex/ChatGPT account-scoped backend calls.

    The browserless provider deliberately reuses the account authenticated by
    Codex. Keep the request shape close to the first-party Codex backend client
    and common ChatGPT backend calls; do not introduce cookies/browser state.
    """
    auth = load_codex_auth(self.auth_path)
    return {
        "Authorization": f"Bearer {auth.access_token}",
        "ChatGPT-Account-ID": auth.account_id,
        "Accept": accept,
        "User-Agent": "codex-cli",
        "OpenAI-Beta": "codex-1",
        "originator": "codex_cli_rs",
        "Origin": "https://chatgpt.com",
        "Referer": "https://chatgpt.com/",
    }


def _validate_auth_with_wham(self: ChatGPTBackendClient) -> dict[str, Any]:
    """Validate Codex OAuth without relying on the browser-oriented /me route.

    /backend-api/wham/usage is an account-scoped endpoint used by Codex clients
    and is a better probe for ~/.codex/auth.json than /backend-api/me, which may
    be rejected by the ChatGPT Web perimeter even when the Codex token is valid.
    """
    payload = self.request_json("GET", "/wham/usage")
    if isinstance(payload, dict):
        return {
            "auth_source": "codex-auth-json",
            "probe": "wham/usage",
            "plan_type": payload.get("plan_type"),
            "rate_limit": payload.get("rate_limit"),
        }
    return {"auth_source": "codex-auth-json", "probe": "wham/usage", "response": payload}


def install_backend_compat() -> None:
    """Install browserless compatibility hooks before the CLI is built."""
    ChatGPTBackendClient._headers = _codex_compatible_headers  # type: ignore[method-assign]
    ChatGPTBackendClient.validate_auth = _validate_auth_with_wham  # type: ignore[method-assign]
