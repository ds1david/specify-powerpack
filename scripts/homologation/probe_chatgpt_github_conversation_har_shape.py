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
from probe_chatgpt_github_conversation_prepare import _init_connector_conversation  # noqa: E402
from probe_chatgpt_github_conversation_submit import (  # noqa: E402
    DEFAULT_PARTIAL_QUERY,
    DEFAULT_PROMPT,
    _inspect_sse_lines,
)


MODEL_RESPONSE_CONTRACTS = [
    {
        "id": "photo_upload_action.v1",
        "protocol_version": 1,
        "presets": ["cap:image", "cap:file", "placement:end"],
    }
]
LOCAL_FUNCTION_NAMES = ["local.continue_in_work"]


def _thinking_effort_for(model: str) -> str | None:
    """Use only the effort observed for the matching HAR model; otherwise fail closed by omission."""
    return "extended" if model == "gpt-5-6-thinking" else None


def _base_client_context() -> dict[str, Any]:
    # These are non-secret product/client shape fields observed in the successful HAR.
    # Values are deliberately generic and are not copied from a browser session.
    return {
        "app_name": "chatgpt.com",
        "has_web_push_capabilities": False,
        "web_push_notification_permission": "default",
    }


def _final_client_context() -> dict[str, Any]:
    return {
        **_base_client_context(),
        "is_dark_mode": False,
        "time_since_loaded": 1,
        "page_height": 1,
        "page_width": 1,
        "pixel_ratio": 1,
        "screen_height": 1,
        "screen_width": 1,
    }


def _prepare_har_shape(
    client: ChatGPTBackendClient,
    *,
    connector_id: str,
    model: str,
    parent_message_id: str,
    partial_query: str,
    timezone: str,
    timezone_offset_min: int,
) -> tuple[str, str, dict[str, Any]]:
    system_hint = f"plugin:{connector_id}"
    body: dict[str, Any] = {
        "action": "next",
        "parent_message_id": parent_message_id,
        "model": model,
        "client_prepare_dispatch": "debounced",
        "client_prepare_source": "composer_editor_state",
        "client_prepare_state": "success",
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "system_hints": [system_hint],
        "model_response_contracts": MODEL_RESPONSE_CONTRACTS,
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "client_contextual_info": _base_client_context(),
        "local_function_names": LOCAL_FUNCTION_NAMES,
        "partial_query": {
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": [partial_query]},
        },
    }
    effort = _thinking_effort_for(model)
    if effort:
        body["thinking_effort"] = effort

    response = client.request_json("POST", "/f/conversation/prepare", body)
    if not isinstance(response, dict):
        raise ProbeError("HAR-shape f/conversation/prepare returned a non-object response")
    conduit_token = str(response.get("conduit_token") or "").strip()
    if not conduit_token:
        raise ProbeError("HAR-shape f/conversation/prepare did not return conduit_token")
    prepare_state = str(response.get("status") or "success").strip() or "success"
    return conduit_token, prepare_state, body


def _build_har_shape_submit_body(
    *,
    connector_id: str,
    model: str,
    parent_message_id: str,
    prompt: str,
    prepare_state: str,
    timezone: str,
    timezone_offset_min: int,
    create_time: float | None = None,
) -> dict[str, Any]:
    stripped = prompt.lstrip()
    if not stripped.casefold().startswith("@github"):
        raise ProbeError("final HAR-shape probe prompt must begin with @GitHub")
    mention_start = prompt.casefold().find("@github")
    mention_end = mention_start + len("@GitHub")
    system_hint = f"plugin:{connector_id}"

    body: dict[str, Any] = {
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
        "parent_message_id": parent_message_id,
        "model": model,
        "client_prepare_state": prepare_state,
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "enable_message_followups": True,
        "system_hints": [system_hint],
        "model_response_contracts": MODEL_RESPONSE_CONTRACTS,
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "client_contextual_info": _final_client_context(),
        "paragen_cot_summary_display_override": "allow",
        "force_parallel_switch": "auto",
        "local_function_names": LOCAL_FUNCTION_NAMES,
    }
    effort = _thinking_effort_for(model)
    if effort:
        body["thinking_effort"] = effort
    return body


def _submit(
    client: ChatGPTBackendClient,
    *,
    body: dict[str, Any],
    conduit_token: str,
) -> tuple[int, dict[str, Any]]:
    headers = client._headers(accept="text/event-stream")
    headers["Content-Type"] = "application/json"
    headers["X-Conduit-Token"] = conduit_token
    # Deliberately omit Sentinel/proof/Turnstile and browser-cookie material.
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
        raw = exc.read()
        if exc.code == 422:
            return int(exc.code), {
                "request_validation_rejected": True,
                "diagnostic": safe_validation_diagnostic(raw),
                "structural_github_tool_evidence": False,
            }
        if exc.code in {401, 403, 429}:
            return int(exc.code), {
                "request_validation_rejected": False,
                "security_or_rate_boundary": True,
                "structural_github_tool_evidence": False,
            }
        raise ChatGPTProjectError(f"HAR-shape final conversation probe failed with HTTP {exc.code}") from exc
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
    connector_id = _resolve_connector(client)
    model, _ = _init_connector_conversation(
        client,
        connector_id,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )
    parent_message_id = str(uuid.uuid4())
    conduit_token, prepare_state, prepare_body = _prepare_har_shape(
        client,
        connector_id=connector_id,
        model=model,
        parent_message_id=parent_message_id,
        partial_query=partial_query,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )
    body = _build_har_shape_submit_body(
        connector_id=connector_id,
        model=model,
        parent_message_id=parent_message_id,
        prompt=prompt,
        prepare_state=prepare_state,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )
    http_status, observed = _submit(client, body=body, conduit_token=conduit_token)

    proven = bool(
        http_status == 200
        and observed.get("assistant_text_seen")
        and observed.get("marker_seen")
        and observed.get("structural_github_tool_evidence")
    )
    classification = (
        "PASS"
        if proven
        else "REQUEST_VALIDATION_REJECTED"
        if http_status == 422
        else "SECURITY_OR_RATE_BOUNDARY"
        if http_status in {401, 403, 429}
        else "BLOCKED_CAPABILITY"
    )
    return {
        "ok": proven,
        "stage": "conversation-har-shape",
        "classification": classification,
        "model": model,
        "request": {
            "prepare_endpoint": "/backend-api/f/conversation/prepare",
            "submit_endpoint": "/backend-api/f/conversation",
            "prepare_har_shape_fields": sorted(prepare_body.keys()),
            "submit_har_shape_fields": sorted(body.keys()),
            "message_create_time_present": True,
            "connector_hint_present": True,
            "message_connector_hint_present": True,
            "ecosystem_mention_present": True,
            "conduit_token_supplied": True,
            "conduit_token_exposed": False,
            "sentinel_or_proof_headers_supplied": False,
            "browser_cookie_material_supplied": False,
        },
        "response": {
            "http_status": http_status,
            **observed,
        },
        "raw_secrets_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the non-secret body shape observed in a successful ChatGPT Web GitHub turn. "
            "The probe intentionally omits Sentinel/proof/Turnstile and browser-cookie material."
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
            "stage": "conversation-har-shape",
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
