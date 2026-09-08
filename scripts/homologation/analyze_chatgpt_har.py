#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


SENSITIVE_HEADER = re.compile(
    r"authorization|cookie|token|secret|session|csrf|oauth|proof|sentinel|conduit",
    re.IGNORECASE,
)
CONNECTOR_RE = re.compile(r"plugin:(connector_[A-Za-z0-9]+)")


def _json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _collect_connectors(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, str):
        result.update(CONNECTOR_RE.findall(value))
        return result
    for item in _walk(value):
        for child in item.values():
            if isinstance(child, str):
                result.update(CONNECTOR_RE.findall(child))
            elif isinstance(child, list):
                for part in child:
                    if isinstance(part, str):
                        result.update(CONNECTOR_RE.findall(part))
    return result


def _body_shape(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    result: dict[str, Any] = {"top_level_keys": sorted(payload.keys())}
    hints = payload.get("system_hints")
    if isinstance(hints, list):
        result["system_hints"] = [
            "plugin:connector_<redacted>" if isinstance(item, str) and item.startswith("plugin:connector_") else item
            for item in hints
        ]
    result["has_plugin_ids"] = "plugin_ids" in payload
    result["has_gizmo_id"] = "gizmo_id" in payload
    mode = payload.get("conversation_mode")
    if isinstance(mode, dict):
        result["conversation_mode_keys"] = sorted(mode.keys())
        result["conversation_mode_kind"] = mode.get("kind")

    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        message = messages[0] if isinstance(messages[0], dict) else {}
        content = message.get("content") if isinstance(message.get("content"), dict) else {}
        parts = content.get("parts") if isinstance(content.get("parts"), list) else []
        first = parts[0] if parts and isinstance(parts[0], str) else ""
        result["first_message_starts_with_github_mention"] = bool(re.match(r"\s*@github\b", first, re.IGNORECASE))
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        mhints = metadata.get("system_hints")
        if isinstance(mhints, list):
            result["message_system_hints"] = [
                "plugin:connector_<redacted>" if isinstance(item, str) and item.startswith("plugin:connector_") else item
                for item in mhints
            ]
        serialization = metadata.get("serialization_metadata")
        if isinstance(serialization, dict):
            offsets = serialization.get("custom_symbol_offsets")
            if isinstance(offsets, list):
                result["custom_symbol_offsets"] = [
                    {
                        "symbol": item.get("symbol"),
                        "startIndex": item.get("startIndex"),
                        "endIndex": item.get("endIndex"),
                        "id_kind": "plugin:connector_<redacted>"
                        if isinstance(item, dict) and str(item.get("id") or "").startswith("plugin:connector_")
                        else "other",
                    }
                    for item in offsets
                    if isinstance(item, dict)
                ]

    partial = payload.get("partial_query")
    if isinstance(partial, dict):
        content = partial.get("content") if isinstance(partial.get("content"), dict) else {}
        parts = content.get("parts") if isinstance(content.get("parts"), list) else []
        first = parts[0] if parts and isinstance(parts[0], str) else ""
        result["partial_query_starts_with_github_text"] = bool(re.match(r"\s*github\b", first, re.IGNORECASE))
    return result


def analyze(path: Path) -> dict[str, Any]:
    har = json.loads(path.read_text(encoding="utf-8"))
    entries = har.get("log", {}).get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("HAR does not contain log.entries")

    rows: list[dict[str, Any]] = []
    connector_ids: set[str] = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        request = entry.get("request") if isinstance(entry.get("request"), dict) else {}
        response = entry.get("response") if isinstance(entry.get("response"), dict) else {}
        url = str(request.get("url") or "")
        post = request.get("postData") if isinstance(request.get("postData"), dict) else {}
        body_text = str(post.get("text") or "")
        payload = _json(body_text)
        connector_ids.update(_collect_connectors(payload if payload is not None else body_text))

        interesting = any(
            token in url
            for token in (
                "/backend-api/conversation",
                "/backend-api/f/conversation",
                "/backend-api/apps/",
                "/backend-api/sentinel/",
                "/realtime/",
            )
        ) or bool(_collect_connectors(payload if payload is not None else body_text)) or bool(
            re.search(r"@github", body_text, re.IGNORECASE)
        )
        if not interesting:
            continue

        request_headers = [
            str(item.get("name"))
            for item in request.get("headers", [])
            if isinstance(item, dict) and item.get("name")
        ]
        response_headers = {
            str(item.get("name") or "").lower(): str(item.get("value") or "")
            for item in response.get("headers", [])
            if isinstance(item, dict)
        }
        event_messages = entry.get("_eventSourceMessages") if isinstance(entry.get("_eventSourceMessages"), list) else []

        rows.append(
            {
                "index": index,
                "startedDateTime": entry.get("startedDateTime"),
                "method": request.get("method"),
                "url": url,
                "status": response.get("status"),
                "request_header_names": sorted(request_headers),
                "sensitive_header_names_present": sorted(
                    name for name in request_headers if SENSITIVE_HEADER.search(name)
                ),
                "response_content_type": response_headers.get("content-type"),
                "body_shape": _body_shape(payload),
                "connector_hint_present": bool(_collect_connectors(payload if payload is not None else body_text)),
                "event_source_event_names": dict(
                    Counter(str(event.get("eventName") or "") for event in event_messages if isinstance(event, dict))
                ),
                "event_source_payloads_exported": any(
                    isinstance(event, dict) and bool(event.get("data")) for event in event_messages
                ),
            }
        )

    return {
        "source": str(path),
        "entry_count": len(entries),
        "connector_count": len(connector_ids),
        "connector_ids": ["connector_<redacted>" for _ in sorted(connector_ids)],
        "raw_secrets_included": False,
        "entries": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect ChatGPT HAR structure without printing credential/header values."
    )
    parser.add_argument("har", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = analyze(args.har)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
