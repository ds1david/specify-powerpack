#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterator
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for value in (SRC, SCRIPT_DIR):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from speckit_powerpack.chatgpt_project_provider import (  # noqa: E402
    ChatGPTBackendClient,
    ChatGPTProjectError,
)
from probe_chatgpt_github_conversation_init import ProbeError  # noqa: E402
from probe_chatgpt_github_conversation_root_parity import (  # noqa: E402
    DEFAULT_PARTIAL_QUERY,
    DEFAULT_PROMPT,
    probe as root_parity_probe,
)


SENSITIVE_KEY = re.compile(
    r"(?:authorization|cookie|set-cookie|token|secret|session|csrf|oauth|proof|sentinel|turnstile|conduit|account[_-]?id|user[_-]?id|email)",
    re.IGNORECASE,
)
SENSITIVE_QUERY_KEY = re.compile(
    r"(?:token|secret|session|csrf|oauth|proof|sentinel|turnstile|conduit|key)",
    re.IGNORECASE,
)
CONNECTOR_ID = re.compile(r"\bconnector_[A-Za-z0-9_-]+\b")
PLUGIN_CONNECTOR_ID = re.compile(r"\bplugin_connector_[A-Za-z0-9_-]+\b")
BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


def _fingerprint(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:10]
    return f"<redacted:{digest}>"


def _redact_text(value: str) -> str:
    rendered = BEARER.sub("Bearer <redacted>", value)
    rendered = PLUGIN_CONNECTOR_ID.sub(lambda m: f"plugin_connector_{_fingerprint(m.group(0))}", rendered)
    rendered = CONNECTOR_ID.sub(lambda m: f"connector_{_fingerprint(m.group(0))}", rendered)
    return rendered


def _sanitize(value: Any, *, key: str | None = None) -> Any:
    if key and SENSITIVE_KEY.search(key):
        if value in (None, "", [], {}):
            return value
        return _fingerprint(str(value))
    if isinstance(value, dict):
        return {str(k): _sanitize(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _safe_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, _fingerprint(value) if SENSITIVE_QUERY_KEY.search(key) and value else value))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query, doseq=True), parsed.fragment)
    )


def _safe_headers(headers: Any) -> dict[str, Any]:
    items = headers.items() if hasattr(headers, "items") else headers or []
    result: dict[str, Any] = {}
    for key, value in items:
        name = str(key)
        text = str(value)
        result[name] = _fingerprint(text) if SENSITIVE_KEY.search(name) and text else _redact_text(text)
    return result


def _decode_body(raw: bytes | str | None, content_type: str = "") -> Any:
    if raw is None:
        return None
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    if not text:
        return ""
    try:
        return _sanitize(json.loads(text))
    except json.JSONDecodeError:
        # Preserve full non-JSON/SSE text structurally, while redacting known identifiers/tokens.
        return _redact_text(text)


class BufferedResponse:
    def __init__(self, *, status: int, headers: Any, body: bytes, url: str):
        self.status = status
        self.code = status
        self.headers = headers
        self._body = body
        self._url = url
        self._buffer = io.BytesIO(body)

    def read(self, amt: int = -1) -> bytes:
        return self._buffer.read(amt)

    def __iter__(self):
        return iter(self._buffer)

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class HttpTraceRecorder:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def request_entry(self, request: urllib.request.Request) -> dict[str, Any]:
        headers = dict(request.header_items())
        content_type = str(headers.get("Content-Type") or headers.get("Content-type") or "")
        return {
            "sequence": len(self.entries) + 1,
            "request": {
                "method": request.get_method(),
                "url": _safe_url(request.full_url),
                "headers": _safe_headers(headers),
                "body": _decode_body(request.data, content_type),
            },
        }

    def complete(
        self,
        entry: dict[str, Any],
        *,
        status: int | None,
        headers: Any = None,
        body: bytes | str | None = None,
        error: str | None = None,
    ) -> None:
        response_headers = _safe_headers(headers or {})
        content_type = ""
        for key, value in response_headers.items():
            if key.casefold() == "content-type":
                content_type = str(value)
                break
        response: dict[str, Any] = {
            "status": status,
            "headers": response_headers,
            "body": _decode_body(body, content_type),
        }
        if error:
            response["error"] = _redact_text(error)
        entry["response"] = response
        self.entries.append(entry)

    def write(self, path: Path) -> None:
        payload = {
            "warning": (
                "HTTP trace is intentionally redacted. Authorization, cookies, OAuth/session/conduit/"
                "Sentinel/proof/Turnstile material and account identifiers are never emitted."
            ),
            "entry_count": len(self.entries),
            "entries": self.entries,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextlib.contextmanager
def trace_urlopen(recorder: HttpTraceRecorder) -> Iterator[None]:
    original = urllib.request.urlopen

    def traced(url, *args, **kwargs):
        request = url if isinstance(url, urllib.request.Request) else urllib.request.Request(url)
        entry = recorder.request_entry(request)
        try:
            response = original(url, *args, **kwargs)
            body = response.read()
            status = int(getattr(response, "status", getattr(response, "code", 0)) or 0)
            headers = getattr(response, "headers", {})
            response_url = response.geturl() if hasattr(response, "geturl") else request.full_url
            recorder.complete(entry, status=status, headers=headers, body=body)
            return BufferedResponse(status=status, headers=headers, body=body, url=response_url)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            recorder.complete(
                entry,
                status=int(exc.code),
                headers=getattr(exc, "headers", {}),
                body=raw,
                error=f"HTTPError: {exc.reason}",
            )
            raise urllib.error.HTTPError(
                exc.url,
                exc.code,
                exc.msg,
                exc.hdrs,
                io.BytesIO(raw),
            ) from exc
        except urllib.error.URLError as exc:
            recorder.complete(entry, status=None, body=None, error=f"URLError: {exc.reason}")
            raise

    urllib.request.urlopen = traced
    try:
        yield
    finally:
        urllib.request.urlopen = original


def run_trace(
    *,
    trace_path: Path,
    output_path: Path | None,
    timezone: str,
    timezone_offset_min: int,
    prompt: str,
    partial_query: str,
    include_partial_query_id: bool,
) -> int:
    recorder = HttpTraceRecorder()
    try:
        with trace_urlopen(recorder):
            report = root_parity_probe(
                ChatGPTBackendClient(),
                timezone=timezone,
                timezone_offset_min=timezone_offset_min,
                prompt=prompt,
                partial_query=partial_query,
                include_partial_query_id=include_partial_query_id,
            )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "conversation-root-parity-http-trace",
            "classification": "BLOCKED_CAPABILITY",
            "error": _redact_text(str(exc)),
        }
    finally:
        recorder.write(trace_path)

    report["http_trace"] = {
        "path": str(trace_path),
        "entry_count": len(recorder.entries),
        "secrets_redacted": True,
    }
    report["raw_secrets_included"] = False
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report.get("ok") else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the GitHub connector root-parity probe with complete redacted HTTP request/response tracing. "
            "URLs, methods, non-secret headers, full JSON bodies and response bodies/SSE are preserved."
        )
    )
    parser.add_argument("--http-log", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--partial-query", default=DEFAULT_PARTIAL_QUERY)
    parser.add_argument("--include-partial-query-id", action="store_true")
    args = parser.parse_args()
    return run_trace(
        trace_path=args.http_log,
        output_path=args.output,
        timezone=args.timezone,
        timezone_offset_min=args.timezone_offset_min,
        prompt=args.prompt,
        partial_query=args.partial_query,
        include_partial_query_id=args.include_partial_query_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
