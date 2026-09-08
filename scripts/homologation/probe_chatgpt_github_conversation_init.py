#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError  # noqa: E402


class ProbeError(RuntimeError):
    pass


def _github_plugins(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        return []
    result: list[dict[str, Any]] = []
    for item in plugins:
        if not isinstance(item, dict):
            continue
        release = item.get("release") if isinstance(item.get("release"), dict) else {}
        names = {
            str(item.get("name") or "").casefold(),
            str(item.get("display_name") or "").casefold(),
            str(release.get("display_name") or "").casefold(),
        }
        if "github" in names:
            result.append(item)
    return result


def _connector_id(plugin: dict[str, Any]) -> str:
    candidates = [plugin.get("connector_id"), plugin.get("canonical_app_id")]
    release = plugin.get("release") if isinstance(plugin.get("release"), dict) else {}
    app_ids = release.get("app_ids") if isinstance(release.get("app_ids"), list) else []
    candidates.extend(app_ids)
    values = [str(value) for value in candidates if isinstance(value, str) and value.startswith("connector_")]
    unique = list(dict.fromkeys(values))
    if len(unique) != 1:
        raise ProbeError("GitHub plugin did not resolve to exactly one canonical connector id")
    return unique[0]


def _resolve_connector(client: ChatGPTBackendClient) -> str:
    installed = client.request_json("GET", "/ps/plugins/installed?limit=1000")
    github = _github_plugins(installed)
    if len(github) != 1:
        raise ProbeError(f"Expected exactly one installed GitHub plugin, found {len(github)}")
    connector_id = _connector_id(github[0])

    # Keep the preflight narrow but meaningful: require the app to still be
    # available before attempting conversation initialization.
    availability_payload = client.request_json(
        "POST",
        "/apps/availability?platform=chat&locale=en-US",
        {"app_ids": [connector_id]},
    )
    items = (
        availability_payload.get("apps")
        if isinstance(availability_payload, dict) and isinstance(availability_payload.get("apps"), list)
        else []
    )
    availability = next(
        (item for item in items if isinstance(item, dict) and item.get("id") == connector_id),
        None,
    )
    if not availability or availability.get("available") is not True or availability.get("installed") is not True:
        raise ProbeError("GitHub connector is not installed and available for chat")
    return connector_id


def probe(
    client: ChatGPTBackendClient,
    *,
    timezone: str = "America/Sao_Paulo",
    timezone_offset_min: int = 180,
) -> dict[str, Any]:
    connector_id = _resolve_connector(client)
    system_hint = f"plugin:{connector_id}"
    body = {
        "requested_default_model": None,
        "conversation_id": None,
        "timezone": timezone,
        "timezone_offset_min": timezone_offset_min,
        "conversation_origin": None,
        "system_hints": [system_hint],
    }

    response = client.request_json("POST", "/conversation/init", body)
    response_keys = sorted(response.keys()) if isinstance(response, dict) else []

    return {
        "ok": True,
        "stage": "conversation-init",
        "request": {
            "endpoint": "/backend-api/conversation/init",
            "connector_hint_present": True,
            "system_hint": "plugin:connector_<redacted>",
            "timezone": timezone,
            "timezone_offset_min": timezone_offset_min,
            "user_prompt_sent": False,
            "github_tool_invoked": False,
        },
        "response": {
            "received": response is not None,
            "top_level_keys": response_keys,
        },
        "raw_secrets_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe whether Codex-derived ChatGPT auth can initialize a connector-aware conversation. "
            "This stage sends no user prompt and does not invoke the GitHub tool."
        )
    )
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--timezone-offset-min", type=int, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = probe(
            ChatGPTBackendClient(),
            timezone=args.timezone,
            timezone_offset_min=args.timezone_offset_min,
        )
    except (ChatGPTProjectError, ProbeError) as exc:
        report = {
            "ok": False,
            "stage": "conversation-init",
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
