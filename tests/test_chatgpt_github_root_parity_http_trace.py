from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import urllib.error
import urllib.request


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "trace_chatgpt_github_root_parity.py"
SPEC = importlib.util.spec_from_file_location("trace_chatgpt_github_root_parity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sanitize_redacts_security_material_but_preserves_request_shape() -> None:
    value = {
        "model": "gpt-5-6-thinking",
        "system_hints": ["plugin:connector_secret123"],
        "conduit_token": "super-secret-conduit",
        "nested": {"Authorization": "Bearer abc.def.ghi", "ordinary": 42},
    }

    safe = MODULE._sanitize(value)

    assert safe["model"] == "gpt-5-6-thinking"
    assert safe["nested"]["ordinary"] == 42
    rendered = json.dumps(safe)
    assert "super-secret-conduit" not in rendered
    assert "abc.def.ghi" not in rendered
    assert "connector_secret123" not in rendered
    assert "<redacted:" in rendered


def test_safe_url_redacts_sensitive_query_values_only() -> None:
    url = MODULE._safe_url("https://chatgpt.com/backend-api/test?limit=100&token=secret-value")

    assert "limit=100" in url
    assert "secret-value" not in url
    assert "token=" in url


def test_trace_urlopen_records_request_and_response_and_replays_body(monkeypatch) -> None:
    class FakeResponse:
        status = 200
        headers = {"Content-Type": "application/json", "Set-Cookie": "secret-cookie"}

        def read(self):
            return b'{"ok":true,"conduit_token":"secret-token"}'

        def geturl(self):
            return "https://chatgpt.com/backend-api/test"

    def fake_urlopen(request, *args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    recorder = MODULE.HttpTraceRecorder()
    request = urllib.request.Request(
        "https://chatgpt.com/backend-api/test",
        data=b'{"system_hints":["plugin:connector_secret123"]}',
        method="POST",
        headers={"Authorization": "Bearer secret-auth", "Content-Type": "application/json"},
    )

    with MODULE.trace_urlopen(recorder):
        with urllib.request.urlopen(request) as response:
            replayed = response.read()

    assert replayed == b'{"ok":true,"conduit_token":"secret-token"}'
    assert len(recorder.entries) == 1
    entry = recorder.entries[0]
    assert entry["request"]["method"] == "POST"
    assert entry["response"]["status"] == 200
    rendered = json.dumps(entry)
    assert "secret-auth" not in rendered
    assert "secret-cookie" not in rendered
    assert "secret-token" not in rendered
    assert "connector_secret123" not in rendered


def test_trace_urlopen_preserves_http_error_body_for_downstream(monkeypatch) -> None:
    def fake_urlopen(request, *args, **kwargs):
        raise urllib.error.HTTPError(
            request.full_url,
            422,
            "Unprocessable Entity",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"detail":"Invalid conversation body"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    recorder = MODULE.HttpTraceRecorder()
    request = urllib.request.Request("https://chatgpt.com/backend-api/f/conversation", method="POST")

    try:
        with MODULE.trace_urlopen(recorder):
            urllib.request.urlopen(request)
    except urllib.error.HTTPError as exc:
        assert exc.code == 422
        assert exc.read() == b'{"detail":"Invalid conversation body"}'
    else:
        raise AssertionError("expected HTTPError")

    assert recorder.entries[0]["response"]["status"] == 422
    assert recorder.entries[0]["response"]["body"] == {"detail": "Invalid conversation body"}
