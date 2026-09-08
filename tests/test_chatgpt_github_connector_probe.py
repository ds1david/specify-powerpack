from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_connector.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_connector", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object | None]] = []

    def request_json(self, method: str, path: str, body=None):
        self.calls.append((method, path, body))
        connector = "connector_test"
        plugin = "plugin_connector_1p_test"
        if path.startswith("/ps/plugins/installed"):
            return {
                "plugins": [
                    {
                        "id": plugin,
                        "name": "github",
                        "canonical_app_id": connector,
                        "connector_id": connector,
                        "status": "ENABLED",
                        "enabled": True,
                        "authentication_policy": "ON_INSTALL",
                        "release": {"display_name": "GitHub", "app_ids": [connector]},
                    }
                ]
            }
        if path == f"/ps/plugins/{plugin}":
            return {
                "id": plugin,
                "name": "github",
                "canonical_app_id": connector,
                "connector_id": connector,
                "status": "ENABLED",
                "release": {"display_name": "GitHub", "app_ids": [connector]},
            }
        if path.startswith("/apps/content"):
            return {
                "apps": [
                    {
                        "id": connector,
                        "name": "GitHub",
                        "status": "ENABLED",
                        "connector_type": "SERVICE",
                    }
                ]
            }
        if path == "/aip/connectors/links/list_accessible":
            return {
                "links": [
                    {
                        "id": "link_secret",
                        "connector_id": connector,
                        "connector_name": "GitHub",
                        "auth_type": "OAUTH",
                        "auth_status": "ACTIVE",
                        "visibility": "VISIBLE",
                        "connector_status": "ENABLED",
                        "apps_privacy_control": "full_access",
                        "oauth_token": "must-not-leak",
                    }
                ]
            }
        if path.startswith("/apps/availability"):
            return {
                "apps": [
                    {
                        "id": connector,
                        "installed": True,
                        "available": True,
                        "can_install": False,
                        "status": "ENABLED",
                    }
                ]
            }
        raise AssertionError(path)


def test_probe_resolves_connector_and_active_authorization_without_exposing_ids() -> None:
    client = FakeClient()

    report = MODULE.probe(client, locale="pt-BR")

    assert report["ok"] is True
    assert report["github_plugin"]["plugin_id"] == "plugin_connector_1p_<redacted>"
    assert report["github_connector"]["connector_id"] == "connector_<redacted>"
    assert report["authorization"]["auth_status"] == "ACTIVE"
    assert report["availability"]["installed"] is True
    assert report["availability"]["available"] is True
    rendered = str(report)
    assert "connector_test" not in rendered
    assert "plugin_connector_1p_test" not in rendered
    assert "link_secret" not in rendered
    assert "must-not-leak" not in rendered


def test_probe_uses_har_observed_read_only_endpoint_sequence() -> None:
    client = FakeClient()

    MODULE.probe(client, locale="pt-BR")

    assert [path for _, path, _ in client.calls] == [
        "/ps/plugins/installed?limit=1000",
        "/ps/plugins/plugin_connector_1p_test",
        "/apps/content?detail=full&platform=chat&locale=pt-BR",
        "/aip/connectors/links/list_accessible",
        "/apps/availability?platform=chat&locale=pt-BR",
    ]
