from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "analyze_chatgpt_plugin_har.py"
SPEC = importlib.util.spec_from_file_location("analyze_chatgpt_plugin_har", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _entry(method: str, url: str, response: dict, request: dict | None = None) -> dict:
    request_data = {
        "method": method,
        "url": url,
        "headers": [
            {"name": "authorization", "value": "Bearer SECRET"},
            {"name": "cookie", "value": "SECRET_COOKIE"},
        ],
    }
    if request is not None:
        request_data["postData"] = {
            "mimeType": "application/json",
            "text": json.dumps(request),
        }
    return {
        "request": request_data,
        "response": {
            "status": 200,
            "content": {
                "mimeType": "application/json",
                "text": json.dumps(response),
            },
        },
    }


def test_plugin_har_analyzer_resolves_github_connector_without_secrets(tmp_path: Path) -> None:
    plugin_id = "plugin_connector_1p_aaaaaaaa"
    connector_id = "connector_bbbbbbbb"
    har = {
        "log": {
            "entries": [
                _entry(
                    "GET",
                    "https://chatgpt.com/backend-api/ps/plugins/installed?limit=1000",
                    {
                        "plugins": [
                            {
                                "id": plugin_id,
                                "name": "github",
                                "canonical_app_id": connector_id,
                                "connector_id": connector_id,
                                "status": "ENABLED",
                                "enabled": True,
                                "authentication_policy": "ON_INSTALL",
                                "release": {
                                    "display_name": "GitHub",
                                    "app_ids": [connector_id],
                                    "requires_local_executor": False,
                                    "interface": {"capabilities": ["Interactive", "Write"]},
                                },
                            }
                        ]
                    },
                ),
                _entry(
                    "GET",
                    f"https://chatgpt.com/backend-api/ps/plugins/{plugin_id}",
                    {
                        "id": plugin_id,
                        "name": "github",
                        "canonical_app_id": connector_id,
                        "connector_id": connector_id,
                        "status": "ENABLED",
                        "release": {"display_name": "GitHub", "app_ids": [connector_id]},
                    },
                ),
                _entry(
                    "POST",
                    "https://chatgpt.com/backend-api/apps/content?detail=full&platform=chat",
                    {
                        "apps": [
                            {
                                "id": connector_id,
                                "name": "GitHub",
                                "status": "ENABLED",
                                "connector_type": "SERVICE",
                                "supported_auth": [{"type": "OAUTH", "token_url": "SECRET"}],
                            }
                        ]
                    },
                    {"app_ids": [connector_id]},
                ),
                _entry(
                    "POST",
                    "https://chatgpt.com/backend-api/aip/connectors/links/list_accessible",
                    {
                        "links": [
                            {
                                "id": "link_cccccccc",
                                "connector_id": connector_id,
                                "connector_name": "GitHub",
                                "auth_type": "OAUTH",
                                "auth_status": "ACTIVE",
                                "visibility": "VISIBLE",
                                "connector_status": "ENABLED",
                                "connector_type": "SERVICE",
                                "apps_privacy_control": "full_access",
                                "oauth_token": "SECRET",
                            }
                        ]
                    },
                    {"principals": [], "link_refresh_strategy": "NONE"},
                ),
                _entry(
                    "GET",
                    f"https://chatgpt.com/backend-api/aip/connectors/{connector_id}/siwc",
                    {"available": False, "email": "secret@example.com", "has_grant": False},
                ),
                _entry(
                    "POST",
                    "https://chatgpt.com/backend-api/apps/availability?platform=chat",
                    {
                        "apps": [
                            {
                                "id": connector_id,
                                "installed": True,
                                "available": True,
                                "can_install": False,
                                "status": "ENABLED",
                            }
                        ]
                    },
                    {"app_ids": [connector_id]},
                ),
            ]
        }
    }
    path = tmp_path / "plugins.har"
    path.write_text(json.dumps(har), encoding="utf-8")

    report = MODULE.analyze(path)
    rendered = json.dumps(report)

    assert report["preflight"] == {
        "github_plugin_resolved": True,
        "connector_mapping_confirmed": True,
        "active_accessible_link": True,
        "app_available": True,
    }
    assert report["installed_catalog"]["plugin_id_kind"] == "plugin_connector_1p_<redacted>"
    assert report["installed_catalog"]["connector_id_kind"] == "connector_<redacted>"
    assert report["accessible_link"]["auth_status"] == "ACTIVE"
    assert report["app_availability"]["available"] is True
    assert "SECRET" not in rendered
    assert "secret@example.com" not in rendered
    assert plugin_id not in rendered
    assert connector_id not in rendered
