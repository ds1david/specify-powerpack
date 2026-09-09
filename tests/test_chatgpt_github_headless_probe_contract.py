from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "homologation" / "probe_chatgpt_github_headless.py"


def _load():
    spec = importlib.util.spec_from_file_location("probe_chatgpt_github_headless", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_headless_probe_does_not_inject_codex_as_web_session() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "load_codex_auth" not in text
    assert "extra_http_headers" not in text
    assert "Bearer" not in text
    assert "codex_auth_injected" in text
    assert "--headed" in text
    assert "--check-only" in text
    assert "--wait-for-login" in text


def test_headless_probe_does_not_log_secrets() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "values_logged=False" in text
    assert "raw_secrets_included" in text
    assert "token" in text
    assert "cookies" in text


def test_headless_probe_fails_closed_before_send_without_connector() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "GITHUB_CONNECTOR_NOT_MATERIALIZED" in text
    assert "send_clicked" in text
    assert "WEB_CHALLENGE_BLOCKED" in text
    assert "WEB_SESSION_REQUIRED" in text
    assert "GOOGLE_IDP_REJECTS_CHROMIUM" in text
    assert "google_sso_rejected_on_chromium" in text
    assert "COMPOSER_READY" in text


def test_headless_probe_documents_google_sso_chromium_dead_end() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Google" in text
    assert "rejects sign-in in Playwright Chromium" in text
    assert "Windows Chrome CDP" in text


def test_default_prompt_requires_github_and_marker() -> None:
    module = _load()

    assert module.DEFAULT_PROMPT.startswith("@GitHub ")
    assert module.MARKER == "POWERPACK_GITHUB_TOOL_OK"
    assert module.MARKER in module.DEFAULT_PROMPT
