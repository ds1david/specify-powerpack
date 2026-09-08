#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any, Iterable
import urllib.error
import urllib.request
import uuid


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
from probe_chatgpt_github_conversation_init import ProbeError, _resolve_connector  # noqa: E402
from probe_chatgpt_github_conversation_prepare import _init_connector_conversation  # noqa: E402


DEFAULT_PROMPT = (
    "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM "
    "POWERPACK_GITHUB_TOOL_OK"
)
DEFAULT_PARTIAL_QUERY = (
    "GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM "
    "POWERPACK_GITHUB_TOOL_OK"
)


class SubmitBlocked(RuntimeError):
    def __init__(self, status: str, message: str, *, http_status: int | None = None):
        super().__init__(message)
        self.status = status
        self.http_status = http_status


def _prepare_ephemeral_state(
    client: ChatGPTBackendClient,
    *,
    timezone: str,
    timezone_offset_min: int,
    partial_query: str,
) -> tuple[str, str, str, str, str]:
    connector_id = _resolve_connector(client)
    model, _ = _init_connector_conversation(
        client,
        connector_id,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )
    parent_message_id = str(uuid.uuid4())
    system_hint = f"plugin:{connector_id}"
    prepare = client.request_json(
        "POST",
        "/f/conversation/prepare",
        {
            "action": "next",
            "parent_message_id": parent_message_id,
            "model": model,
            "conversation_mode": {"kind": "primary_assistant"},
            "system_hints": [system_hint],
            "partial_query": {
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [partial_query]},
            },
            "supports_buffering": True,
        },
    )
    if not isinstance(prepare, dict):
        raise ProbeError("f/conversation/prepare returned a non-object response")
    conduit_token = str(prepare.get("conduit_token") or "").strip()
    if not conduit_token:
        raise ProbeError("f/conversation/prepare did not return conduit_token")
    prepare_state = str(prepare.get("status") or "success").strip() or "success"
    return connector_id, model, parent_message_id, conduit_token, prepare_state


def _build_submit_body(
    *,
    connector_id: str,
    model: str,
    parent_message_id: str,
    prompt: str,
    prepare_state: str,
    timezone: str,
    timezone_offset_min: int,
) -> dict[str, Any]:
    if not prompt.lstrip().casefold().startswith("@github"):
        raise ProbeError("final probe prompt must begin with @GitHub")
    mention_start = prompt.casefold().find("@github")
    mention_end = mention_start + len("@GitHub")
    system_hint = f"plugin:{connector_id}"
    return {
        "action": "next",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [prompt]},
                "metadata": {
                    "system_hints": [system_hint],
                    "serialization_metadata": {
                        "custom_symbol_offsets": [
                            {
                                "id": system_hint,
                                "symbol": "ecosystemMention",
                                "startIndex": mention_start,
                                "endIndex": mention_end,
                            }
                        ]
                    },
                    "submission_mode": "manual_send",
                },
            }
        ],
        "parent_message_id": parent_message_id,
        "model": model,
        "client_prepare_state": prepare_state,
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "enable_message_followups": True,
        "system_hints": [system_hint],
        "supports_buffering": True,
        "supported_encodings": ["v1"],
    }


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _has_structural_github_tool_evidence(event: Any) -> bool:
    if not isinstance(event, dict):
        return False
    for item in _walk(event):
        if not isinstance(item, dict):
            continue
        recipient = item.get("recipient")
        if isinstance(recipient, str) and "github" in recipient.casefold():
            return True
        tool_name = item.get("tool_name")
        if isinstance(tool_name, str) and "github" in tool_name.casefold():
            return True
        author = item.get("author")
        if isinstance(author, dict):
            role = str(author.get("role") or "").casefold()
            name = str(author.get("name") or "").casefold()
            if role == "tool" and "github" in name:
                return True
        content_type = str(item.get("content_type") or "").casefold()
        if content_type in {"tool_result", "execution_output"}:
            serialized = json.dumps(item, ensure_ascii=False).casefold()
            if "github" in serialized:
                return True
    return False


def _inspect_sse_lines(lines: Iterable[str]) -> dict[str, Any]:
    event_types: Counter[str] = Counter()
    event_count = 0
    assistant_text_seen = False
    marker_seen = False
    structural_github_tool_evidence = False

    for raw in lines:
        line = raw.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        event_count += 1
        if isinstance(event, dict):
            event_type = str(event.get("type") or "message")
            event_types[event_type] += 1
            serialized = json.dumps(event, ensure_ascii=False)
            if "POWERPACK_GITHUB_TOOL_OK" in serialized:
                marker_seen = True
            if any(
                key in serialized
                for key in (
                    '"role": "assistant"',
                    '"author": {"role": "assistant"',
                    '"delta"',
                )
            ):
                assistant_text_seen = True
            structural_github_tool_evidence = (
                structural_github_tool_evidence
                or _has_structural_github_tool_evidence(event)
            )

    return {
        "event_count": event_count,
        "event_types": dict(event_types),
        "assistant_text_seen": assistant_text_seen,
        "marker_seen": marker_seen,
        "structural_github_tool_evidence": structural_github_tool_evidence,
    }


def _submit(
    client: ChatGPTBackendClient,
    *,
    body: dict[str, Any],
    conduit_token: str,
) -> tuple[int, dict[str, Any]]:
    headers = client._headers(accept="text/event-stream")  # experimental probe; same authenticated client
    headers["Content-Type"] = "application/json"
    headers["X-Conduit-Token"] = conduit_token
    # Deliberately do not fabricate or obtain Sentinel/proof/Turnstile headers.
    request = urllib.request.Request(
        f"{BACKEND_API}/f/conversation",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=max(client.timeout, 120)) as response:
            lines = (raw.decode("utf-8", errors="replace") for raw in response)
            return int(response.status), _inspect_sse_lines(lines)
    except urllib.error.HTTPError as exc:
        # Do not surface the private backend body because it may contain dynamic
        # security/session diagnostics. The HTTP status is sufficient evidence.
        if exc.code in {401, 403, 429}:
            raise SubmitBlocked(
                "BLOCKED_CAPABILITY",
                "Final connector-aware conversation submission was rejected without fabricated Sentinel/proof material.",
                http_status=int(exc.code),
            ) from exc
        raise ChatGPTProjectError(
            f"ChatGPT final conversation probe failed with HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ChatGPTProjectError(f"Cannot reach ChatGPT final conversation endpoint: {exc}") from exc


def probe(
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

    try:
        http_status, observed = _submit(client, body=body, conduit_token=conduit_token)
    except SubmitBlocked as exc:
        return {
            "ok": False,
            "stage": "conversation-submit",
            "blocked_status": exc.status,
            "request": {
                "endpoint": "/backend-api/f/conversation",
                "connector_hint_present": True,
                "message_connector_hint_present": True,
                "ecosystem_mention_present": True,
                "conduit_token_supplied": True,
                "conduit_token_exposed": False,
                "sentinel_or_proof_headers_supplied": False,
                "final_user_message_sent": True,
            },
            "response": {
                "http_status": exc.http_status,
                "transport_accepted": False,
                "structural_github_tool_evidence": False,
            },
            "raw_secrets_included": False,
        }

    proven = bool(
        http_status == 200
        and observed.get("assistant_text_seen")
        and observed.get("marker_seen")
        and observed.get("structural_github_tool_evidence")
    )
    return {
        "ok": proven,
        "stage": "conversation-submit",
        "blocked_status": None if proven else "BLOCKED_CAPABILITY",
        "request": {
            "endpoint": "/backend-api/f/conversation",
            "connector_hint_present": True,
            "message_connector_hint_present": True,
            "ecosystem_mention_present": True,
            "conduit_token_supplied": True,
            "conduit_token_exposed": False,
            "sentinel_or_proof_headers_supplied": False,
            "final_user_message_sent": True,
        },
        "response": {
            "http_status": http_status,
            "transport_accepted": http_status == 200,
            **observed,
        },
        "raw_secrets_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe the final connector-aware ChatGPT conversation submission using only a legitimately returned conduit token. "
            "The probe never fabricates Sentinel/proof/Turnstile material and fails closed if the backend requires it."
        )
    )
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--partial-query", default=DEFAULT_PARTIAL_QUERY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = probe(
            ChatGPTBackendClient(),
            timezone=args.timezone,
            timezone_offset_min=args.timezone_offset_min,
            prompt=args.prompt,
            partial_query=args.partial_query,
        )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "conversation-submit",
            "blocked_status": "BLOCKED_CAPABILITY",
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
