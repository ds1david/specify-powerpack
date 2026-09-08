#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for value in (SRC, SCRIPT_DIR):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from speckit_powerpack.chatgpt_project_provider import (  # noqa: E402
    BACKEND_API,
    ChatGPTBackendClient,
    ChatGPTProjectError,
)
from probe_chatgpt_github_conversation_init import ProbeError  # noqa: E402
from probe_chatgpt_github_conversation_submit import (  # noqa: E402
    DEFAULT_PARTIAL_QUERY,
    DEFAULT_PROMPT,
    _build_submit_body,
    _prepare_ephemeral_state,
)


SENSITIVE_TEXT = re.compile(
    r"(?:bearer\s+\S+|connector_[A-Za-z0-9]+|plugin_connector_[A-Za-z0-9_]+|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def _redact_text(value: str) -> str:
    return SENSITIVE_TEXT.sub("<redacted>", value)


def _safe_loc(value: Any) -> list[str | int]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str | int] = []
    for item in value[:12]:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str):
            result.append(_redact_text(item)[:160])
    return result


def safe_validation_diagnostic(raw: bytes | str) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {
            "json": False,
            "body_exposed": False,
            "validation_errors": [],
        }

    report: dict[str, Any] = {
        "json": True,
        "body_exposed": False,
        "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        "validation_errors": [],
    }
    if not isinstance(payload, dict):
        return report

    detail = payload.get("detail")
    if isinstance(detail, list):
        errors: list[dict[str, Any]] = []
        for item in detail[:20]:
            if not isinstance(item, dict):
                continue
            safe: dict[str, Any] = {}
            if isinstance(item.get("type"), str):
                safe["type"] = _redact_text(item["type"])[:160]
            loc = _safe_loc(item.get("loc"))
            if loc:
                safe["loc"] = loc
            if isinstance(item.get("msg"), str):
                safe["msg"] = _redact_text(item["msg"])[:300]
            if safe:
                errors.append(safe)
        report["validation_errors"] = errors
    elif isinstance(detail, str):
        report["detail_message"] = _redact_text(detail)[:300]

    error = payload.get("error")
    if isinstance(error, dict):
        safe_error: dict[str, str] = {}
        for key in ("type", "code", "message"):
            value = error.get(key)
            if isinstance(value, str):
                safe_error[key] = _redact_text(value)[:300]
        if safe_error:
            report["error"] = safe_error

    return report


def diagnose(
    client: ChatGPTBackendClient,
    *,
    timezone: str = "America/Sao_Paulo",
    timezone_offset_min: int = 180,
    prompt: str = DEFAULT_PROMPT,
    partial_query: str = DEFAULT_PARTIAL_QUERY,
) -> dict[str, Any]:
    connector_id, model, parent_message_id, conduit_token, prepare_state = _prepare_ephemeral_state(
        client,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
        partial_query=partial_query,
    )
    body = _build_submit_body(
        connector_id=connector_id,
        model=model,
        parent_message_id=parent_message_id,
        prompt=prompt,
        prepare_state=prepare_state,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )

    headers = client._headers(accept="text/event-stream")
    headers["Content-Type"] = "application/json"
    headers["X-Conduit-Token"] = conduit_token
    request = urllib.request.Request(
        f"{BACKEND_API}/f/conversation",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=max(client.timeout, 120)) as response:
            # This diagnostic is only intended to explain schema rejection. If
            # the request is accepted, do not consume or expose the conversation.
            return {
                "ok": True,
                "stage": "conversation-submit-diagnostic",
                "http_status": int(response.status),
                "request_validation_rejected": False,
                "note": "Request was accepted; use the normal submit probe for SSE/tool evidence.",
                "raw_secrets_included": False,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        diagnostic = safe_validation_diagnostic(raw) if exc.code == 422 else {
            "json": False,
            "body_exposed": False,
            "validation_errors": [],
        }
        return {
            "ok": False,
            "stage": "conversation-submit-diagnostic",
            "http_status": int(exc.code),
            "request_validation_rejected": exc.code == 422,
            "diagnostic": diagnostic,
            "raw_secrets_included": False,
        }
    except urllib.error.URLError as exc:
        raise ChatGPTProjectError(f"Cannot reach ChatGPT final conversation endpoint: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safely diagnose HTTP 422 from the connector-aware final ChatGPT conversation submit. "
            "Only validation type/location/message are emitted; request inputs, ids and tokens are never printed."
        )
    )
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--partial-query", default=DEFAULT_PARTIAL_QUERY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = diagnose(
            ChatGPTBackendClient(),
            timezone=args.timezone,
            timezone_offset_min=args.timezone_offset_min,
            prompt=args.prompt,
            partial_query=args.partial_query,
        )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "conversation-submit-diagnostic",
            "error": str(exc),
            "raw_secrets_included": False,
        }

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
