from __future__ import annotations

import importlib
from pathlib import Path

from speckit_powerpack import request_log


def test_curl_formats_method_url_and_body():
    assert request_log.curl("get", "https://x/y") == "curl -sS -X GET 'https://x/y'"
    line = request_log.curl("POST", "https://x/y", b'{"a": 1}')
    assert line.startswith("curl -sS -X POST 'https://x/y' --data-raw ")
    assert '{"a": 1}' in line


def test_curl_redacts_bearer_tokens_and_pats_in_the_body():
    body = (
        '{"tools":[{"type":"mcp","server_url":"https://api.githubcopilot.com/mcp/",'
        '"headers":{"Authorization":"Bearer github_pat_11ABCDE0000fake_TOKEN_value"}}]}'
    )
    line = request_log.curl("POST", "https://x", body)
    assert "github_pat_11ABCDE0000fake_TOKEN_value" not in line
    assert "Bearer <redacted>" in line
    assert '"type":"mcp"' in line  # non-secret content is preserved
    bare = request_log.curl("POST", "https://x", '{"t":"ghp_abcdefghijklmnop1234"}')
    assert "ghp_abcdefghijklmnop1234" not in bare and "gh" in bare


def test_curl_raw_mode_keeps_headers_secrets_and_full_body(monkeypatch):
    monkeypatch.setenv("SPECKIT_POWERPACK_HTTP_LOG_RAW", "1")
    headers = {"Authorization": "Bearer sk-live-SECRET", "Cookie": "oai-did=abc"}
    big_body = "A" * 9000 + "END_MARKER"
    line = request_log.curl("POST", "https://x", big_body, headers)
    assert "-H 'Authorization: Bearer sk-live-SECRET'" in line
    assert "-H 'Cookie: oai-did=abc'" in line
    assert "Bearer <redacted>" not in line  # no redaction in raw mode
    assert "…[+" not in line and "END_MARKER" in line  # full body, untruncated
    assert " \\\n  " in line  # one flag per continuation line


def test_curl_raw_mode_off_by_default_still_drops_headers():
    line = request_log.curl("GET", "https://x", None, {"Authorization": "Bearer x"})
    assert line == "curl -sS -X GET 'https://x'"


def test_curl_truncates_a_long_body():
    line = request_log.curl("POST", "https://x", "z" * 9000)
    assert "…[+" in line and "bytes]" in line
    assert len(line) < 9000


def test_log_request_is_a_noop_without_the_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECKIT_POWERPACK_HTTP_LOG", raising=False)
    request_log.log_request("GET", "https://x")  # must not raise / create anything
    assert not list(tmp_path.iterdir())


def test_log_request_appends_curl_lines_when_env_set(monkeypatch, tmp_path: Path):
    target = tmp_path / "sub" / "http.log"
    monkeypatch.setenv("SPECKIT_POWERPACK_HTTP_LOG", str(target))
    request_log.log_request("GET", "https://chatgpt.com/backend-api/wham/usage")
    request_log.log_note("codex exec: codex exec --json '<prompt: 42 chars>'")
    request_log.log_request("POST", "https://chatgpt.com/backend-api/codex/responses", b'{"model":"x"}')
    text = target.read_text(encoding="utf-8")
    assert "curl -sS -X GET 'https://chatgpt.com/backend-api/wham/usage'" in text
    assert "# " in text and "codex exec --json" in text
    assert "--data-raw '{\"model\":\"x\"}'" in text
    assert text.count("curl -sS") == 2  # the note is not a curl line


def test_request_json_traces_the_call(monkeypatch, tmp_path: Path):
    target = tmp_path / "http.log"
    monkeypatch.setenv("SPECKIT_POWERPACK_HTTP_LOG", str(target))
    provider = importlib.import_module("speckit_powerpack.chatgpt_project_provider")

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    monkeypatch.setattr(provider.urllib.request, "urlopen", lambda *a, **k: _Resp())
    monkeypatch.setattr(
        provider.ChatGPTBackendClient, "_headers",
        lambda self, *, accept="application/json": {"Accept": accept},
    )
    provider.ChatGPTBackendClient().request_json("GET", "/wham/usage")
    assert "curl -sS -X GET 'https://chatgpt.com/backend-api/wham/usage'" in target.read_text("utf-8")
