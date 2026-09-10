from __future__ import annotations

import importlib
from pathlib import Path

from speckit_powerpack import request_log


def test_curl_formats_method_url_and_body():
    assert request_log.curl("get", "https://x/y") == "curl -sS -X GET 'https://x/y'"
    line = request_log.curl("POST", "https://x/y", b'{"a": 1}')
    assert line.startswith("curl -sS -X POST 'https://x/y' --data-raw ")
    assert '{"a": 1}' in line


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
