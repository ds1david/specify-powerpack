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

CLIENT_CREATED_ROOT = "client-created-root"
MODEL_RESPONSE_CONTRACTS = [
    {
        "id": "photo_upload_action.v1",
        "protocol_version": 1,
        "presets": ["cap:image", "cap:file", "placement:end"],
    }
]
LOCAL_FUNCTION_NAMES = ["local.continue_in_work"]


def _thinking_effort_for(model: str) -> str | None:
    return "extended" if model == "gpt-5-6-thinking" else None


def _base_client_context() -> dict[str, Any]:
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


def _prepare_body(
    *,
    connector_id: str,
    model: str,
    partial_query: str,
    timezone: str,
    timezone_offset_min: int,
    include_partial_query_id: bool,
) -> dict[str, Any]:
    system_hint = f"plugin:{connector_id}"
    partial: dict[str, Any] = {
        "author": {"role": "user"},
        "content": {"content_type": "text", "parts": [partial_query]},
    }
    if include_partial_query_id:
        partial["id"] = str(uuid.uuid4())

    body: dict[str, Any] = {
        "action": "next",
        "parent_message_id": CLIENT_CREATED_ROOT,
        "model": model,
        "client_prepare_state": "success",
        "client_prepare_dispatch": "debounced",
        "client_prepare_source": "composer_editor_state",
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "system_hints": [system_hint],
        "model_response_contracts": MODEL_RESPONSE_CONTRACTS,
        "partial_query": partial,
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "client_contextual_info": _base_client_context(),
        "local_function_names": LOCAL_FUNCTION_NAMES,
    }
    effort = _thinking_effort_for(model)
    if effort:
        body["thinking_effort"] = effort
    return body


def _submit_body(
    *,
    connector_id: str,
    model: str,
    prompt: str,
    prepare_state: str,
    timezone: str,
    timezone_offset_min: int,
) -> dict[str, Any]:
    if not prompt.lstrip().casefold().startswith("@github"):
        raise ProbeError("root-parity final prompt must begin with @GitHub")
    mention_start = prompt.casefold().find("@github")
    mention_end = mention_start + len("@GitHub")
    system_hint = f"plugin:{connector_id}"

    body: dict[str, Any] = {
        "action": "next",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "author": {"role": "user"},
                "create_time": time.time(),
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


def probe(
    client: ChatGPTBackendClient,
    *,
    timezone: str = "America/Sao_Paulo",
    timezone_offset_min: int = 180,
    prompt: str = DEFAULT_PROMPT,
    partial_query: str = DEFAULT_PARTIAL_QUERY,
    include_partial_query_id: bool = False,
) -> dict[str, Any]:
    connector_id = _resolve_connector(client)
    model, _ = _init_connector_conversation(
        client,
        connector_id,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )

    prepare_body = _prepare_body(
        connector_id=connector_id,
        model=model,
        partial_query=partial_query,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
        include_partial_query_id=include_partial_query_id,
    )
    prepare = client.request_json("POST", "/f/conversation/prepare", prepare_body)
    if not isinstance(prepare, dict):
        raise ProbeError("root-parity prepare returned a non-object response")
    conduit_token = str(prepare.get("conduit_token") or "").strip()
    if not conduit_token:
        raise ProbeError("root-parity prepare did not return conduit_token")
    prepare_state = str(prepare.get("status") or "success").strip() or "success"

    body = _submit_body(
        connector_id=connector_id,
        model=model,
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
            lines = (raw.decode("utf-8", errors="replace") for raw in response)
            observed = _inspect_sse_lines(lines)
            status = int(response.status)
            proven = bool(
                status == 200
                and observed.get("assistant_text_seen")
                and observed.get("marker_seen")
                and observed.get("structural_github_tool_evidence")
            )
            return {
                "ok": proven,
                "stage": "conversation-root-parity",
                "classification": "GITHUB_TOOL_PROVEN" if proven else "TRANSPORT_ACCEPTED_TOOL_NOT_PROVEN",
                "model": model,
                "request": {
                    "parent_message_id_semantics": CLIENT_CREATED_ROOT,
                    "partial_query_id_present": include_partial_query_id,
                    "connector_hint_present": True,
                    "ecosystem_mention_present": True,
                    "conduit_token_supplied": True,
                    "conduit_token_exposed": False,
                    "sentinel_or_proof_headers_supplied": False,
                    "browser_cookie_material_supplied": False,
                },
                "response": {
                    "http_status": status,
                    "transport_accepted": status == 200,
                    **observed,
                },
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
            raise ChatGPTProjectError(f"root-parity final submit failed with HTTP {exc.code}") from exc
        return {
            "ok": False,
            "stage": "conversation-root-parity",
            "classification": classification,
            "model": model,
            "request": {
                "parent_message_id_semantics": CLIENT_CREATED_ROOT,
                "partial_query_id_present": include_partial_query_id,
                "connector_hint_present": True,
                "ecosystem_mention_present": True,
                "conduit_token_supplied": True,
                "conduit_token_exposed": False,
                "sentinel_or_proof_headers_supplied": False,
                "browser_cookie_material_supplied": False,
            },
            "response": {
                "http_status": int(exc.code),
                "transport_accepted": False,
                "diagnostic": diagnostic,
                "structural_github_tool_evidence": False,
            },
            "raw_secrets_included": False,
        }
    except urllib.error.URLError as exc:
        raise ChatGPTProjectError(f"Cannot reach ChatGPT root-parity final endpoint: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe the successful HAR's client-created-root parent semantics without fabricating product-security material. "
            "Use --include-partial-query-id as a second ablation if root parity alone still returns 422."
        )
    )
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--partial-query", default=DEFAULT_PARTIAL_QUERY)
    parser.add_argument("--include-partial-query-id", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = probe(
            ChatGPTBackendClient(),
            timezone=args.timezone,
            timezone_offset_min=args.timezone_offset_min,
            prompt=args.prompt,
            partial_query=args.partial_query,
            include_partial_query_id=args.include_partial_query_id,
        )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "conversation-root-parity",
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
