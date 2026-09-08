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
from probe_chatgpt_github_conversation_init import ProbeError  # noqa: E402
from probe_chatgpt_github_conversation_submit import (  # noqa: E402
    DEFAULT_PARTIAL_QUERY,
    DEFAULT_PROMPT,
    _inspect_sse_lines,
    _prepare_ephemeral_state,
)


def _build_har_parity_body(
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

    # Body fields below were observed in the successful Edge HAR final
    # /backend-api/f/conversation request. Values that are product/UI context
    # rather than credentials are represented with generic browserless values;
    # no Sentinel/proof/Turnstile material is fabricated or replayed.
    return {
        "action": "next",
        "messages": [
            {
                "id": __import__("uuid").uuid4().hex,
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
        "parent_message_id": parent_message_id,
        "model": model,
        "client_prepare_state": prepare_state,
        "timezone_offset_min": timezone_offset_min,
        "timezone": timezone,
        "conversation_mode": {"kind": "primary_assistant"},
        "enable_message_followups": True,
        "system_hints": [system_hint],
        "model_response_contracts": [
            {
                "id": "photo_upload_action.v1",
                "protocol_version": 1,
                "presets": ["cap:image", "cap:file", "placement:end"],
            }
        ],
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "client_contextual_info": {
            "is_dark_mode": False,
            "time_since_loaded": 0,
            "page_height": 900,
            "page_width": 1200,
            "pixel_ratio": 1,
            "screen_height": 1080,
            "screen_width": 1920,
            "app_name": "chatgpt.com",
            "has_web_push_capabilities": False,
            "web_push_notification_permission": "default",
        },
        "paragen_cot_summary_display_override": "allow",
        "force_parallel_switch": "auto",
        "thinking_effort": "extended",
        "local_function_names": ["local.continue_in_work"],
    }


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
    body = _build_har_parity_body(
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
                "stage": "conversation-submit-har-parity",
                "blocked_status": None if proven else "BLOCKED_CAPABILITY",
                "request": {
                    "endpoint": "/backend-api/f/conversation",
                    "har_body_parity_fields_present": True,
                    "connector_hint_present": True,
                    "ecosystem_mention_present": True,
                    "conduit_token_supplied": True,
                    "conduit_token_exposed": False,
                    "sentinel_or_proof_headers_supplied": False,
                    "final_user_message_sent": True,
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
        diagnostic = safe_validation_diagnostic(raw) if exc.code == 422 else None
        return {
            "ok": False,
            "stage": "conversation-submit-har-parity",
            "blocked_status": "BLOCKED_CAPABILITY",
            "request": {
                "endpoint": "/backend-api/f/conversation",
                "har_body_parity_fields_present": True,
                "connector_hint_present": True,
                "ecosystem_mention_present": True,
                "conduit_token_supplied": True,
                "conduit_token_exposed": False,
                "sentinel_or_proof_headers_supplied": False,
                "final_user_message_sent": True,
            },
            "response": {
                "http_status": int(exc.code),
                "transport_accepted": False,
                "request_validation_rejected": exc.code == 422,
                "diagnostic": diagnostic,
                "structural_github_tool_evidence": False,
            },
            "raw_secrets_included": False,
        }
    except urllib.error.URLError as exc:
        raise ChatGPTProjectError(f"Cannot reach ChatGPT final conversation endpoint: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Submit one connector-aware ChatGPT turn using the non-secret request-body fields observed in the successful Edge HAR. "
            "The probe still omits Sentinel/proof/Turnstile headers and never prints connector, conduit, OAuth or session secrets."
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
            "stage": "conversation-submit-har-parity",
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
