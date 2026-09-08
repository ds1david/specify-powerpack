from __future__ import annotations

from speckit_powerpack.github_connector_discovery import discover_github_connector


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object | None]] = []

    def request_json(self, method: str, path: str, body=None):
        self.calls.append((method, path, body))
        connector = "connector_test"
        plugin = "plugin_connector_1p_test"
        if path == "/ps/plugins/installed?limit=1000":
            return {"plugins": [{"id": plugin, "name": "github", "connector_id": connector, "canonical_app_id": connector, "status": "ENABLED", "enabled": True, "authentication_policy": "ON_INSTALL", "release": {"display_name": "GitHub", "app_ids": [connector]}}]}
        if path == f"/ps/plugins/{plugin}":
            return {"id": plugin, "name": "github", "connector_id": connector, "canonical_app_id": connector, "status": "ENABLED", "release": {"display_name": "GitHub", "app_ids": [connector]}}
        if path.startswith("/apps/content"):
            return {"apps": [{"id": connector, "name": "GitHub", "status": "ENABLED", "connector_type": "SERVICE"}]}
        if path == "/aip/connectors/links/list_accessible":
            return {"links": [{"id": "link_test", "connector_id": connector, "connector_name": "GitHub", "auth_type": "OAUTH", "auth_status": "ACTIVE", "visibility": "VISIBLE", "connector_status": "ENABLED", "apps_privacy_control": "full_access"}]}
        if path.startswith("/apps/availability"):
            return {"apps": [{"id": connector, "installed": True, "available": True, "can_install": False, "status": "ENABLED"}]}
        raise AssertionError(path)


def test_discovery_uses_observed_backend_sequence() -> None:
    client = FakeClient()
    state = discover_github_connector(client, locale="pt-BR")
    assert state.ok is True
    assert [(method, path) for method, path, _ in client.calls] == [
        ("GET", "/ps/plugins/installed?limit=1000"),
        ("GET", "/ps/plugins/plugin_connector_1p_test"),
        ("POST", "/apps/content?detail=full&platform=chat&locale=pt-BR"),
        ("POST", "/aip/connectors/links/list_accessible"),
        ("POST", "/apps/availability?platform=chat&locale=pt-BR"),
    ]


def test_safe_report_redacts_plugin_connector_and_link_ids() -> None:
    state = discover_github_connector(FakeClient(), locale="pt-BR")
    report = state.safe_report()
    rendered = str(report)
    assert report["ok"] is True
    assert report["github_plugin"]["status"] == "ENABLED"
    assert report["github_connector"]["connector_type"] == "SERVICE"
    assert report["authorization"]["auth_type"] == "OAUTH"
    assert report["authorization"]["auth_status"] == "ACTIVE"
    assert report["availability"]["installed"] is True
    assert report["availability"]["available"] is True
    assert "connector_test" not in rendered
    assert "plugin_connector_1p_test" not in rendered
    assert "link_test" not in rendered
