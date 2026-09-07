from __future__ import annotations

import json
from pathlib import Path

from speckit_powerpack.backend_compat import (
    _codex_compatible_headers,
    _validate_auth_with_wham,
)
from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient


def _auth_file(tmp_path: Path) -> Path:
    path = tmp_path / "auth.json"
    path.write_text(
        json.dumps({"tokens": {"access_token": "token", "account_id": "acct-test"}}),
        encoding="utf-8",
    )
    return path


def test_codex_compatible_headers_include_account_and_codex_hints(tmp_path: Path) -> None:
    client = ChatGPTBackendClient(_auth_file(tmp_path))

    headers = _codex_compatible_headers(client)

    assert headers["Authorization"] == "Bearer token"
    assert headers["ChatGPT-Account-ID"] == "acct-test"
    assert headers["OpenAI-Beta"] == "codex-1"
    assert headers["originator"] == "codex_cli_rs"
    assert headers["Origin"] == "https://chatgpt.com"
    assert headers["Referer"] == "https://chatgpt.com/"


def test_auth_probe_uses_wham_usage_not_me(monkeypatch, tmp_path: Path) -> None:
    client = ChatGPTBackendClient(_auth_file(tmp_path))
    calls: list[tuple[str, str]] = []

    def fake_request(method: str, path: str, body=None):
        calls.append((method, path))
        return {"plan_type": "plus", "rate_limit": {"primary_window": {"used_percent": 10}}}

    monkeypatch.setattr(client, "request_json", fake_request)

    result = _validate_auth_with_wham(client)

    assert calls == [("GET", "/wham/usage")]
    assert result["probe"] == "wham/usage"
    assert result["plan_type"] == "plus"
