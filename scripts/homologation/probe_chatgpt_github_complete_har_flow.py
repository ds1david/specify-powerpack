#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any
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
from diagnose_chatgpt_github_submit_422 import safe_validation_diagnostic  # noqa: E402
from probe_chatgpt_github_conversation_init import ProbeError, _resolve_connector  # noqa: E402
from probe_chatgpt_github_conversation_submit import DEFAULT_PROMPT  # noqa: E402


CLIENT_CREATED_ROOT = "client-created-root"
HAR_MODEL = "gpt-5.6-sol-wm"
HAR_THINKING_EFFORT = "xhigh"
HAR_CONVERSATION_ORIGIN = "tpp"
MODEL_RESPONSE_CONTRACTS = [
    {
        "id": "photo_upload_action.v1",
        "protocol_version": 1,
        "presets": ["cap:image", "cap:file", "placement:end"],
    }
]
LOCAL_FUNCTION_NAMES = ["local.continue_in_work"]


def _client_context_base() -> dict[str, Any]:
    return {
        "app_name": "chatgpt.com",
        "has_web_push_capabilities": False,
        "web_push_notification_permission": "default",
    }


def _client_context_final() -> dict[str, Any]:
    return {
        "is_dark_mode": False,
        "time_since_loaded": 1,
        "page_height": 1,
        "page_width": 1,
        "pixel_ratio": 1,
        "screen_height": 1,
        "screen_width": 1,
        **_client_context_base(),
    }


def _initial_init_body(*, timezone: str, timezone_offset_min: int) -> dict[str, Any]:
    return {
        "requested_default_model": None,
        "conversation_id": None,
        "timezone": timezone,
        "timezone_offset_min": timezone_offset_min,
        "conversation_origin": HAR_CONVERSATION_ORIGIN,
    }


def _unresolved_prepare_body(
    *,
    prompt: str,
    model: str,
    thinking_effort: str,
    timezone: str,
    timezone_offset_min: int,
) -> dict[str, Any]:
    return {
        "action": "next",
        "parent_message_id": CLIENT_CREATED_ROOT,
        "model": model,
        "client_prepare_state": "none",
        "client_prepare_dispatch": "debounced",
        "client_prepare_source": "composer_editor_state",
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "system_hints": [],
        "model_response_contracts": MODEL_RESPONSE_CONTRACTS,
        "partial_query": {
            "id": str(uuid.uuid4()),
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": [prompt]},
        },
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "conversation_origin": HAR_CONVERSATION_ORIGIN,
        "client_contextual_info": _client_context_base(),
        "thinking_effort": thinking_effort,
        "local_function_names": LOCAL_FUNCTION_NAMES,
    }


def _connector_init_body(
    *,
    connector_id: str,
    timezone: str,
    timezone_offset_min: int,
) -> dict[str, Any]:
    return {
        **_initial_init_body(timezone=timezone, timezone_offset_min=timezone_offset_min),
        "system_hints": [f"plugin:{connector_id}"],
    }


def _without_github_at(prompt: str) -> str:
    stripped = prompt.lstrip()
    if not stripped.casefold().startswith("@github"):
        raise ProbeError("complete HAR probe prompt must begin with @GitHub")
    prefix_len = len(prompt) - len(stripped)
    return (prompt[:prefix_len] + stripped[len("@GitHub"):].lstrip()).lstrip()


def _connector_prepare_body(
    *,
    connector_id: str,
    prompt: str,
    model: str,
    thinking_effort: str,
    timezone: str,
    timezone_offset_min: int,
) -> dict[str, Any]:
    system_hint = f"plugin:{connector_id}"
    return {
        "action": "next",
        "parent_message_id": CLIENT_CREATED_ROOT,
        "model": model,
        "client_prepare_state": "sent",
        "client_prepare_dispatch": "immediate",
        "client_prepare_source": "context_change",
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "system_hints": [system_hint],
        "model_response_contracts": MODEL_RESPONSE_CONTRACTS,
        "partial_query": {
            "id": str(uuid.uuid4()),
            "author": {"role": "user"},
            "content": {
                "content_type": "text",
                "parts": [_without_github_at(prompt)],
            },
        },
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "conversation_origin": HAR_CONVERSATION_ORIGIN,
        "client_contextual_info": _client_context_base(),
        "thinking_effort": thinking_effort,
        "local_function_names": LOCAL_FUNCTION_NAMES,
    }


def _final_submit_body(
    *,
    connector_id: str,
    prompt: str,
    model: str,
    thinking_effort: str,
    timezone: str,
    timezone_offset_min: int,
    create_time: float | None = None,
) -> dict[str, Any]:
    stripped = prompt.lstrip()
    if not stripped.casefold().startswith("@github"):
        raise ProbeError("complete HAR probe prompt must begin with @GitHub")
    mention_start = prompt.casefold().find("@github")
    mention_end = mention_start + len("@GitHub")
    system_hint = f"plugin:{connector_id}"
    return {
        "action": "next",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "author": {"role": "user"},
                "create_time": float(create_time if create_time is not None else time.time()),
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
        "parent_message_id": CLIENT_CREATED_ROOT,
        "model": model,
        # Important: the real prepare HTTP response says status=ok, but the
        # accepted final HAR body uses client_prepare_state=success.
        "client_prepare_state": "success",
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "enable_message_followups": True,
        "system_hints": [system_hint],
        "model_response_contracts": MODEL_RESPONSE_CONTRACTS,
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "conversation_origin": HAR_CONVERSATION_ORIGIN,
        "client_contextual_info": _client_context_final(),
        "paragen_cot_summary_display_override": "allow",
        "force_parallel_switch": "auto",
        "thinking_effort": thinking_effort,
        "local_function_names": LOCAL_FUNCTION_NAMES,
    }


def _inspect_handoff(lines) -> dict[str, Any]:
    event_count = 0
    resume_token_seen = False
    stream_handoff_seen = False
    conversation_id_present = False
    turn_exchange_id_present = False
    for raw in lines:
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_count += 1
        event_type = str(event.get("type") or "")
        if event_type == "resume_conversation_token":
            resume_token_seen = True
            conversation_id_present = conversation_id_present or bool(event.get("conversation_id"))
        elif event_type == "stream_handoff":
            stream_handoff_seen = True
            conversation_id_present = conversation_id_present or bool(event.get("conversation_id"))
            turn_exchange_id_present = bool(event.get("turn_exchange_id"))
    return {
        "event_count": event_count,
        "resume_conversation_token_seen": resume_token_seen,
        "stream_handoff_seen": stream_handoff_seen,
        "conversation_id_present": conversation_id_present,
        "turn_exchange_id_present": turn_exchange_id_present,
        "token_values_exposed": False,
    }


def probe(
    client: ChatGPTBackendClient,
    *,
    prompt: str = DEFAULT_PROMPT,
    model: str = HAR_MODEL,
    thinking_effort: str = HAR_THINKING_EFFORT,
    timezone: str = "America/Sao_Paulo",
    timezone_offset_min: int = 180,
) -> dict[str, Any]:
    if not prompt.lstrip().casefold().startswith("@github"):
        raise ProbeError("complete HAR probe prompt must begin with @GitHub")

    # Reproduce the observed UI sequence, while resolving the connector through
    # the already-proven account/plugin preflight rather than hard-coding it.
    client.request_json(
        "POST",
        "/conversation/init",
        _initial_init_body(timezone=timezone, timezone_offset_min=timezone_offset_min),
    )
    unresolved = client.request_json(
        "POST",
        "/f/conversation/prepare",
        _unresolved_prepare_body(
            prompt=prompt,
            model=model,
            thinking_effort=thinking_effort,
            timezone=timezone,
            timezone_offset_min=timezone_offset_min,
        ),
    )
    if not isinstance(unresolved, dict) or not unresolved.get("conduit_token"):
        raise ProbeError("unresolved @GitHub prepare did not return conduit_token")

    connector_id = _resolve_connector(client)
    client.request_json(
        "POST",
        "/conversation/init",
        _connector_init_body(
            connector_id=connector_id,
            timezone=timezone,
            timezone_offset_min=timezone_offset_min,
        ),
    )
    connector_prepare = client.request_json(
        "POST",
        "/f/conversation/prepare",
        _connector_prepare_body(
            connector_id=connector_id,
            prompt=prompt,
            model=model,
            thinking_effort=thinking_effort,
            timezone=timezone,
            timezone_offset_min=timezone_offset_min,
        ),
    )
    if not isinstance(connector_prepare, dict):
        raise ProbeError("connector-aware prepare returned a non-object response")
    conduit_token = str(connector_prepare.get("conduit_token") or "").strip()
    if not conduit_token:
        raise ProbeError("connector-aware prepare did not return conduit_token")

    body = _final_submit_body(
        connector_id=connector_id,
        prompt=prompt,
        model=model,
        thinking_effort=thinking_effort,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )
    headers = client._headers(accept="text/event-stream")
    headers["Content-Type"] = "application/json"
    headers["X-Conduit-Token"] = conduit_token
    # Deliberately do not fabricate/replay Sentinel/proof/Turnstile or browser
    # cookie material. This probe only corrects the non-secret HAR semantics.
    request = urllib.request.Request(
        f"{BACKEND_API}/f/conversation",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=max(client.timeout, 120)) as response:
            status = int(response.status)
            observed = _inspect_handoff(response)
            return {
                "ok": status == 200,
                "stage": "complete-har-flow",
                "classification": "TRANSPORT_ACCEPTED_HANDOFF" if status == 200 else "BLOCKED_CAPABILITY",
                "request": {
                    "initial_unresolved_prepare": True,
                    "connector_context_change_prepare": True,
                    "final_client_prepare_state": "success",
                    "conversation_origin": HAR_CONVERSATION_ORIGIN,
                    "model": model,
                    "thinking_effort": thinking_effort,
                    "connector_hint_present": True,
                    "ecosystem_mention_present": True,
                    "conduit_token_supplied": True,
                    "conduit_token_exposed": False,
                    "sentinel_or_proof_headers_supplied": False,
                    "browser_cookie_material_supplied": False,
                },
                "response": {"http_status": status, **observed},
                "raw_secrets_included": False,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        if exc.code == 422:
            classification = "REQUEST_VALIDATION_REJECTED"
            diagnostic = safe_validation_diagnostic(raw)
        elif exc.code in {401, 403, 429}:
            classification = "SECURITY_OR_RATE_BOUNDARY"
            diagnostic = None
        else:
            raise ChatGPTProjectError(f"complete HAR final submit failed with HTTP {exc.code}") from exc
        return {
            "ok": False,
            "stage": "complete-har-flow",
            "classification": classification,
            "request": {
                "initial_unresolved_prepare": True,
                "connector_context_change_prepare": True,
                "final_client_prepare_state": "success",
                "conversation_origin": HAR_CONVERSATION_ORIGIN,
                "model": model,
                "thinking_effort": thinking_effort,
                "connector_hint_present": True,
                "ecosystem_mention_present": True,
                "conduit_token_supplied": True,
                "conduit_token_exposed": False,
                "sentinel_or_proof_headers_supplied": False,
                "browser_cookie_material_supplied": False,
            },
            "response": {
                "http_status": int(exc.code),
                "diagnostic": diagnostic,
            },
            "raw_secrets_included": False,
        }
    except urllib.error.URLError as exc:
        raise ChatGPTProjectError(f"Cannot reach ChatGPT complete-HAR final endpoint: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the non-secret turn semantics observed in the complete successful @GitHub HAR. "
            "No Sentinel/proof/Turnstile or browser-cookie material is fabricated or replayed."
        )
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=HAR_MODEL)
    parser.add_argument("--thinking-effort", default=HAR_THINKING_EFFORT)
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = probe(
            ChatGPTBackendClient(),
            prompt=args.prompt,
            model=args.model,
            thinking_effort=args.thinking_effort,
            timezone=args.timezone,
            timezone_offset_min=args.timezone_offset_min,
        )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "complete-har-flow",
            "classification": "BLOCKED_CAPABILITY",
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
