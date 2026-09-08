#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PLUGIN_INSTALLED = "/backend-api/ps/plugins/installed"
PLUGIN_DETAIL_PREFIX = "/backend-api/ps/plugins/plugin_connector_"
APPS_CONTENT = "/backend-api/apps/content"
LINKS_ACCESSIBLE = "/backend-api/aip/connectors/links/list_accessible"
APPS_AVAILABILITY = "/backend-api/apps/availability"
CONNECTOR_PREFIX = "/backend-api/aip/connectors/connector_"


def _response_text(entry: dict[str, Any]) -> str:
    content = entry.get("response", {}).get("content", {})
    text = str(content.get("text") or "")
    if content.get("encoding") == "base64" and text:
        try:
            return base64.b64decode(text).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return text


def _json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def _request_json(entry: dict[str, Any]) -> Any | None:
    post = entry.get("request", {}).get("postData", {})
    return _json(str(post.get("text") or ""))


def _redacted_id_kind(value: Any) -> str | None:
    text = str(value or "")
    if text.startswith("plugin_connector_1p_"):
        return "plugin_connector_1p_<redacted>"
    if text.startswith("connector_"):
        return "connector_<redacted>"
    if text.startswith("plugin:connector_"):
        return "plugin:connector_<redacted>"
    if text.startswith("link_"):
        return "link_<redacted>"
    return None


def _github_plugin(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    candidates: list[dict[str, Any]] = []
    plugins = payload.get("plugins")
    if isinstance(plugins, list):
        candidates.extend(item for item in plugins if isinstance(item, dict))
    elif "id" in payload:
        candidates.append(payload)
    for item in candidates:
        release = item.get("release") if isinstance(item.get("release"), dict) else {}
        names = {
            str(item.get("name") or "").casefold(),
            str(item.get("display_name") or "").casefold(),
            str(release.get("display_name") or "").casefold(),
        }
        if "github" in names:
            return item
    return None


def _summarize_plugin(item: dict[str, Any]) -> dict[str, Any]:
    release = item.get("release") if isinstance(item.get("release"), dict) else {}
    interface = release.get("interface") if isinstance(release.get("interface"), dict) else {}
    app_ids = release.get("app_ids") if isinstance(release.get("app_ids"), list) else []
    return {
        "found": True,
        "plugin_id_kind": _redacted_id_kind(item.get("id")),
        "name": item.get("name") or item.get("display_name") or release.get("display_name"),
        "canonical_app_id_kind": _redacted_id_kind(item.get("canonical_app_id")),
        "connector_id_kind": _redacted_id_kind(item.get("connector_id")),
        "release_app_id_kinds": [_redacted_id_kind(value) for value in app_ids],
        "status": item.get("status"),
        "enabled": item.get("enabled"),
        "authentication_policy": item.get("authentication_policy"),
        "requires_local_executor": release.get("requires_local_executor"),
        "capabilities": interface.get("capabilities"),
    }


def _safe_header_names(entry: dict[str, Any]) -> list[str]:
    request = entry.get("request") if isinstance(entry.get("request"), dict) else {}
    return sorted(
        str(item.get("name"))
        for item in request.get("headers", [])
        if isinstance(item, dict) and item.get("name")
    )


def analyze(path: Path) -> dict[str, Any]:
    har = json.loads(path.read_text(encoding="utf-8"))
    entries = har.get("log", {}).get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("HAR does not contain log.entries")

    report: dict[str, Any] = {
        "source": str(path),
        "entry_count": len(entries),
        "raw_secret_values_included": False,
        "installed_catalog": None,
        "plugin_detail": None,
        "app_content": None,
        "accessible_link": None,
        "connector_probe": None,
        "app_availability": None,
        "sequence": [],
    }

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        request = entry.get("request") if isinstance(entry.get("request"), dict) else {}
        url = str(request.get("url") or "")
        path_only = urlparse(url).path
        method = str(request.get("method") or "")
        status = entry.get("response", {}).get("status")
        payload = _json(_response_text(entry))

        if path_only == PLUGIN_INSTALLED:
            plugin = _github_plugin(payload)
            if plugin:
                report["installed_catalog"] = _summarize_plugin(plugin)
                report["sequence"].append({"index": index, "method": method, "path": path_only, "status": status})

        elif path_only.startswith(PLUGIN_DETAIL_PREFIX):
            plugin = _github_plugin(payload)
            if plugin:
                report["plugin_detail"] = _summarize_plugin(plugin)
                report["sequence"].append({"index": index, "method": method, "path": "/backend-api/ps/plugins/plugin_connector_1p_<redacted>", "status": status})

        elif path_only == APPS_CONTENT:
            req = _request_json(entry)
            apps = payload.get("apps") if isinstance(payload, dict) and isinstance(payload.get("apps"), list) else []
            github = next((item for item in apps if isinstance(item, dict) and str(item.get("name") or "").casefold() == "github"), None)
            if github:
                app_ids = req.get("app_ids") if isinstance(req, dict) and isinstance(req.get("app_ids"), list) else []
                report["app_content"] = {
                    "request_app_id_kinds": [_redacted_id_kind(value) for value in app_ids],
                    "id_kind": _redacted_id_kind(github.get("id")),
                    "name": github.get("name"),
                    "status": github.get("status"),
                    "connector_type": github.get("connector_type"),
                    "supported_auth_types": [
                        auth.get("type") for auth in github.get("supported_auth", [])
                        if isinstance(auth, dict) and auth.get("type")
                    ],
                }
                report["sequence"].append({"index": index, "method": method, "path": path_only, "status": status})

        elif path_only == LINKS_ACCESSIBLE:
            links = payload.get("links") if isinstance(payload, dict) and isinstance(payload.get("links"), list) else []
            github = next((item for item in links if isinstance(item, dict) and str(item.get("connector_name") or item.get("name") or "").casefold() == "github"), None)
            if github:
                report["accessible_link"] = {
                    "link_id_kind": _redacted_id_kind(github.get("id")),
                    "connector_id_kind": _redacted_id_kind(github.get("connector_id")),
                    "name": github.get("connector_name") or github.get("name"),
                    "auth_type": github.get("auth_type"),
                    "auth_status": github.get("auth_status"),
                    "visibility": github.get("visibility"),
                    "connector_status": github.get("connector_status"),
                    "connector_type": github.get("connector_type"),
                    "apps_privacy_control": github.get("apps_privacy_control"),
                }
                report["sequence"].append({"index": index, "method": method, "path": path_only, "status": status})

        elif path_only.startswith(CONNECTOR_PREFIX) and path_only.endswith("/siwc"):
            report["connector_probe"] = {
                "path": "/backend-api/aip/connectors/connector_<redacted>/siwc",
                "response_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
                "available": payload.get("available") if isinstance(payload, dict) else None,
                "has_grant": payload.get("has_grant") if isinstance(payload, dict) else None,
            }
            report["sequence"].append({"index": index, "method": method, "path": "/backend-api/aip/connectors/connector_<redacted>/siwc", "status": status})

        elif path_only == APPS_AVAILABILITY:
            req = _request_json(entry)
            apps = payload.get("apps") if isinstance(payload, dict) and isinstance(payload.get("apps"), list) else []
            github = next((item for item in apps if isinstance(item, dict) and _redacted_id_kind(item.get("id")) == "connector_<redacted>"), None)
            if github:
                app_ids = req.get("app_ids") if isinstance(req, dict) and isinstance(req.get("app_ids"), list) else []
                report["app_availability"] = {
                    "request_app_id_kinds": [_redacted_id_kind(value) for value in app_ids],
                    "id_kind": _redacted_id_kind(github.get("id")),
                    "installed": github.get("installed"),
                    "available": github.get("available"),
                    "can_install": github.get("can_install"),
                    "status": github.get("status"),
                }
                report["sequence"].append({"index": index, "method": method, "path": path_only, "status": status})

    report["preflight"] = {
        "github_plugin_resolved": bool(report["installed_catalog"]),
        "connector_mapping_confirmed": bool(
            report["installed_catalog"]
            and report["installed_catalog"].get("connector_id_kind") == "connector_<redacted>"
        ),
        "active_accessible_link": bool(
            report["accessible_link"]
            and report["accessible_link"].get("auth_status") == "ACTIVE"
        ),
        "app_available": bool(
            report["app_availability"]
            and report["app_availability"].get("available") is True
            and report["app_availability"].get("installed") is True
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect ChatGPT plugin-selection HAR structure without printing credential values."
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
