from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .chatgpt_project_provider import ChatGPTBackendClient


class GitHubConnectorDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubConnectorDiscovery:
    plugin_id: str
    connector_id: str
    plugin_status: str
    plugin_enabled: bool | None
    authentication_policy: str | None
    connector_status: str
    connector_type: str | None
    auth_type: str | None
    auth_status: str
    authorization_link_found: bool
    visibility: str | None
    apps_privacy_control: str | None
    availability_status: str
    installed: bool
    available: bool
    can_install: bool | None

    @property
    def ok(self) -> bool:
        return bool(
            self.plugin_status == "ENABLED"
            and self.connector_status == "ENABLED"
            # The Web conversation may request authorization through the
            # explicit JIT confirm_action/allow flow. ACTIVE is evidence, not
            # a discovery-time precondition.
            and self.authorization_link_found
            and self.availability_status == "ENABLED"
            and self.installed
            and self.available
        )

    def safe_report(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "github_plugin": {
                "resolved": True,
                "status": self.plugin_status,
                "enabled": self.plugin_enabled,
                "authentication_policy": self.authentication_policy,
                "plugin_id": "plugin_connector_1p_<redacted>",
            },
            "github_connector": {
                "resolved": True,
                "connector_id": "connector_<redacted>",
                "metadata_status": self.connector_status,
                "connector_type": self.connector_type,
            },
            "authorization": {
                "accessible_link_found": True,
                "auth_type": self.auth_type,
                "auth_status": self.auth_status,
                "visibility": self.visibility,
                "connector_status": self.connector_status,
                "apps_privacy_control": self.apps_privacy_control,
            },
            "availability": {
                "found": True,
                "installed": self.installed,
                "available": self.available,
                "can_install": self.can_install,
                "status": self.availability_status,
            },
            "api_sequence": [
                "GET /backend-api/ps/plugins/installed?limit=1000",
                "GET /backend-api/ps/plugins/plugin_connector_1p_<redacted>",
                "POST /backend-api/apps/content?detail=full&platform=chat&locale=<locale>",
                "POST /backend-api/aip/connectors/links/list_accessible",
                "POST /backend-api/apps/availability?platform=chat&locale=<locale>",
            ],
            "raw_secrets_included": False,
        }


def _github_plugins(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("plugins"), list):
        return []
    result: list[dict[str, Any]] = []
    for item in payload["plugins"]:
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
    release = plugin.get("release") if isinstance(plugin.get("release"), dict) else {}
    app_ids = release.get("app_ids") if isinstance(release.get("app_ids"), list) else []
    candidates = [plugin.get("connector_id"), plugin.get("canonical_app_id"), *app_ids]
    values = [
        str(value)
        for value in candidates
        if isinstance(value, str) and value.startswith("connector_")
    ]
    unique = list(dict.fromkeys(values))
    if len(unique) != 1:
        raise GitHubConnectorDiscoveryError(
            "GitHub plugin did not resolve to exactly one canonical connector id"
        )
    return unique[0]


def discover_github_connector(
    client: ChatGPTBackendClient,
    *,
    locale: str = "pt-BR",
) -> GitHubConnectorDiscovery:
    installed_payload = client.request_json("GET", "/ps/plugins/installed?limit=1000")
    github_plugins = _github_plugins(installed_payload)
    if len(github_plugins) != 1:
        raise GitHubConnectorDiscoveryError(
            f"Expected exactly one installed GitHub plugin, found {len(github_plugins)}"
        )

    plugin = github_plugins[0]
    plugin_id = str(plugin.get("id") or "")
    if not plugin_id.startswith("plugin_connector_1p_"):
        raise GitHubConnectorDiscoveryError(
            "Installed GitHub entry did not expose the expected plugin connector identity"
        )
    connector_id = _connector_id(plugin)

    detail = client.request_json("GET", f"/ps/plugins/{plugin_id}")
    if not isinstance(detail, dict) or _connector_id(detail) != connector_id:
        raise GitHubConnectorDiscoveryError(
            "GitHub plugin detail did not confirm the canonical connector id"
        )

    content = client.request_json(
        "POST",
        f"/apps/content?detail=full&platform=chat&locale={locale}",
        {"app_ids": [connector_id]},
    )
    apps = content.get("apps") if isinstance(content, dict) and isinstance(content.get("apps"), list) else []
    app = next(
        (
            item
            for item in apps
            if isinstance(item, dict)
            and item.get("id") == connector_id
            and str(item.get("name") or "").casefold() == "github"
        ),
        None,
    )
    if not app:
        raise GitHubConnectorDiscoveryError(
            "GitHub connector metadata was not returned by apps/content"
        )

    links_payload = client.request_json(
        "POST",
        "/aip/connectors/links/list_accessible",
        {"principals": [], "link_refresh_strategy": "NONE"},
    )
    links = links_payload.get("links") if isinstance(links_payload, dict) and isinstance(links_payload.get("links"), list) else []
    link = next(
        (
            item
            for item in links
            if isinstance(item, dict)
            and item.get("connector_id") == connector_id
            and str(item.get("connector_name") or item.get("name") or "").casefold() == "github"
        ),
        None,
    )
    if not link:
        raise GitHubConnectorDiscoveryError(
            "No GitHub connector authorization link was returned for this account"
        )

    availability_payload = client.request_json(
        "POST",
        f"/apps/availability?platform=chat&locale={locale}",
        {"app_ids": [connector_id]},
    )
    availability_items = (
        availability_payload.get("apps")
        if isinstance(availability_payload, dict)
        and isinstance(availability_payload.get("apps"), list)
        else []
    )
    availability = next(
        (
            item
            for item in availability_items
            if isinstance(item, dict) and item.get("id") == connector_id
        ),
        None,
    )
    if not availability:
        raise GitHubConnectorDiscoveryError(
            "GitHub connector availability was not returned"
        )

    state = GitHubConnectorDiscovery(
        plugin_id=plugin_id,
        connector_id=connector_id,
        plugin_status=str(plugin.get("status") or "").upper(),
        plugin_enabled=plugin.get("enabled") if isinstance(plugin.get("enabled"), bool) else None,
        authentication_policy=str(plugin.get("authentication_policy") or "") or None,
        connector_status=str(app.get("status") or link.get("connector_status") or "").upper(),
        connector_type=str(app.get("connector_type") or "") or None,
        auth_type=str(link.get("auth_type") or "") or None,
        auth_status=str(link.get("auth_status") or "").upper(),
        authorization_link_found=True,
        visibility=str(link.get("visibility") or "") or None,
        apps_privacy_control=str(link.get("apps_privacy_control") or "") or None,
        availability_status=str(availability.get("status") or "").upper(),
        installed=availability.get("installed") is True,
        available=availability.get("available") is True,
        can_install=availability.get("can_install") if isinstance(availability.get("can_install"), bool) else None,
    )
    if not state.ok:
        raise GitHubConnectorDiscoveryError(
            "GitHub connector was discovered but is not enabled/available for this account"
        )
    return state
