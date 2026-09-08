#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
import uuid


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for value in (SRC, SCRIPT_DIR):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError  # noqa: E402
from probe_chatgpt_github_conversation_init import ProbeError, _resolve_connector  # noqa: E402


def _init_connector_conversation(
    client: ChatGPTBackendClient,
    connector_id: str,
    *,
    timezone: str,
    timezone_offset_min: int,
) -> tuple[str, dict[str, Any]]:
    response = client.request_json(
        "POST",
        "/conversation/init",
        {
            "requested_default_model": None,
            "conversation_id": None,
            "timezone": timezone,
            "timezone_offset_min": timezone_offset_min,
            "conversation_origin": None,
            "system_hints": [f"plugin:{connector_id}"],
        },
    )
    if not isinstance(response, dict):
        raise ProbeError("conversation/init returned a non-object response")
    model = str(response.get("default_model_slug") or "").strip()
    if not model:
        raise ProbeError("conversation/init did not return default_model_slug")
    return model, response


def probe(
    client: ChatGPTBackendClient,
    *,
    timezone: str = "America/Sao_Paulo",
    timezone_offset_min: int = 180,
    partial_query: str = "GitHub LISTE TODOS OS MEUS REPOSITORIOS",
) -> dict[str, Any]:
    connector_id = _resolve_connector(client)
    system_hint = f"plugin:{connector_id}"
    model, init_response = _init_connector_conversation(
        client,
        connector_id,
        timezone=timezone,
        timezone_offset_min=timezone_offset_min,
    )

    parent_message_id = str(uuid.uuid4())
    prepare_body = {
        "action": "next",
        "parent_message_id": parent_message_id,
        "model": model,
        "conversation_mode": {"kind": "primary_assistant"},
        "system_hints": [system_hint],
        "partial_query": {
            "author": {"role": "user"},
            "content": {
                "content_type": "text",
                "parts": [partial_query],
            },
        },
        "supports_buffering": True,
    }
    prepare_response = client.request_json("POST", "/f/conversation/prepare", prepare_body)
    if not isinstance(prepare_response, dict):
        raise ProbeError("f/conversation/prepare returned a non-object response")

    conduit_present = bool(str(prepare_response.get("conduit_token") or "").strip())
    response_keys = sorted(prepare_response.keys())
    init_keys = sorted(init_response.keys())

    return {
        "ok": conduit_present,
        "stage": "conversation-prepare",
        "request": {
            "init_endpoint": "/backend-api/conversation/init",
            "prepare_endpoint": "/backend-api/f/conversation/prepare",
            "connector_hint_present": True,
            "system_hint": "plugin:connector_<redacted>",
            "conversation_mode_kind": "primary_assistant",
            "model_resolved_from_init": True,
            "parent_message_id_generated": True,
            "partial_query_sent": True,
            "partial_query_starts_with_github_text": partial_query.lstrip().casefold().startswith("github"),
            "final_user_message_sent": False,
            "github_tool_invoked": False,
        },
        "response": {
            "init_top_level_keys": init_keys,
            "prepare_received": True,
            "prepare_top_level_keys": response_keys,
            "conduit_token_present": conduit_present,
            "conduit_token_exposed": False,
        },
        "raw_secrets_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe whether Codex-derived ChatGPT auth can prepare a connector-aware conversation turn. "
            "The conduit token is only checked for presence and is never printed. "
            "No final user message is submitted and the GitHub tool is not invoked."
        )
    )
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--partial-query", default="GitHub LISTE TODOS OS MEUS REPOSITORIOS")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = probe(
            ChatGPTBackendClient(),
            timezone=args.timezone,
            timezone_offset_min=args.timezone_offset_min,
            partial_query=args.partial_query,
        )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "conversation-prepare",
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
