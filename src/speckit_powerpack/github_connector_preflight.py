from __future__ import annotations

from typing import Any

from .chatgpt_project_provider import ChatGPTBackendClient


class GitHubConnectorError(RuntimeError):
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
    candidates = [
        plugin.get("connector_id"),
        plugin.get("canonical_app_id"),
    ]
    release = plugin.get("release") if isinstance(plugin.get("release"), dict) else {}
    app_ids = release.get("app_ids") if isinstance(release.get("app_ids"), list) else []
    candidates.extend(app_ids)
    values = [str(value) for value in candidates if isinstance(value, str) and value.startswith("connector_")]
    unique = list(dict.fromkeys(values))
    if len(unique) != 1:
        raise GitHubConnectorError("GitHub plugin did not resolve to exactly one canonical connector id")
    return unique[0]


def discover_github_connector(client: ChatGPTBackendClient, *, locale: str = "en-US") -> dict[str, Any]:
    """Resolve the installed GitHub plugin without printing ids or OAuth material."""
    installed = client.request_json("GET", "/ps/plugins/installed?limit=1000")
    github = _github_plugins(installed)
    if len(github) != 1:
        raise GitHubConnectorError(f"Expected exactly one installed GitHub plugin, found {len(github)}")

    plugin = github[0]
    plugin_id = str(plugin.get("id") or "")
    if not plugin_id.startswith("plugin_connector_1p_"):
        raise GitHubConnectorError("Installed GitHub entry did not expose the expected plugin connector identity")
    connector_id = _connector_id(plugin)

    detail = client.request_json("GET", f"/ps/plugins/{plugin_id}")
    if not isinstance(detail, dict) or _connector_id(detail) != connector_id:
        raise GitHubConnectorError("GitHub plugin detail did not confirm the canonical connector id")

    content = client.request_json(
        "POST",
        f"/apps/content?detail=full&platform=chat&locale={locale}",
        {"app_ids": [connector_id]},
    )
    apps = content.get("apps") if isinstance(content, dict) and isinstance(content.get("apps"), list) else []
    app = next(
        (
            item for item in apps
            if isinstance(item, dict)
            and item.get("id") == connector_id
            and str(item.get("name") or "").casefold() == "github"
        ),
        None,
    )
    if not app:
        raise GitHubConnectorError("GitHub connector metadata was not returned by apps/content")

    links_payload = client.request_json(
        "POST",
        "/aip/connectors/links/list_accessible",
        {"principals": [], "link_refresh_strategy": "NONE"},
    )
    links = links_payload.get("links") if isinstance(links_payload, dict) and isinstance(links_payload.get("links"), list) else []
    link = next(
        (
            item for item in links
            if isinstance(item, dict)
            and item.get("connector_id") == connector_id
            and str(item.get("connector_name") or item.get("name") or "").casefold() == "github"
        ),
        None,
    )

    availability_payload = client.request_json(
        "POST",
        f"/apps/availability?platform=chat&locale={locale}",
        {"app_ids": [connector_id]},
    )
    availability_items = (
        availability_payload.get("apps")
        if isinstance(availability_payload, dict) and isinstance(availability_payload.get("apps"), list)
        else []
    )
    availability = next(
        (
            item for item in availability_items
            if isinstance(item, dict) and item.get("id") == connector_id
        ),
        None,
    )

    ok = bool(
        str(plugin.get("status") or "").upper() == "ENABLED"
        and app.get("status") == "ENABLED"
        and link
        and link.get("auth_status") == "ACTIVE"
        and availability
        and availability.get("installed") is True
        and availability.get("available") is True
        and availability.get("status") == "ENABLED"
    )
    return {
        "ok": ok,
        "github_plugin": {
            "resolved": True,
            "status": plugin.get("status"),
            "enabled": plugin.get("enabled"),
            "authentication_policy": plugin.get("authentication_policy"),
            "plugin_id": "plugin_connector_1p_<redacted>",
        },
        "github_connector": {
            "resolved": True,
            "connector_id": "connector_<redacted>",
            "metadata_status": app.get("status"),
            "connector_type": app.get("connector_type"),
        },
        "authorization": {
            "accessible_link_found": bool(link),
            "auth_type": link.get("auth_type") if link else None,
            "auth_status": link.get("auth_status") if link else None,
            "visibility": link.get("visibility") if link else None,
            "connector_status": link.get("connector_status") if link else None,
            "apps_privacy_control": link.get("apps_privacy_control") if link else None,
        },
        "availability": {
            "found": bool(availability),
            "installed": availability.get("installed") if availability else None,
            "available": availability.get("available") if availability else None,
            "can_install": availability.get("can_install") if availability else None,
            "status": availability.get("status") if availability else None,
        },
        "raw_secrets_included": False,
    }


def probe(client: ChatGPTBackendClient, *, locale: str = "en-US") -> dict[str, Any]:
    """Backward-compatible alias used by the homologation connector probe."""
    return discover_github_connector(client, locale=locale)
