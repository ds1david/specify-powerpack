from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_conversation_init.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_conversation_init", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object | None]] = []

    def request_json(self, method: str, path: str, body=None):
        self.calls.append((method, path, body))
        connector = "connector_test"
        if path.startswith("/ps/plugins/installed"):
            return {
                "plugins": [
                    {
                        "id": "plugin_connector_1p_test",
                        "name": "github",
                        "canonical_app_id": connector,
                        "connector_id": connector,
                        "release": {"display_name": "GitHub", "app_ids": [connector]},
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
                        "status": "ENABLED",
                    }
                ]
            }
        if path == "/conversation/init":
            assert isinstance(body, dict)
            assert body["system_hints"] == ["plugin:connector_test"]
            assert body["conversation_id"] is None
            return {
                "conversation_id": "conversation_secret",
                "default_model_slug": "model_test",
                "some_metadata": True,
            }
        raise AssertionError(path)


def test_probe_initializes_conversation_with_resolved_connector_hint() -> None:
    client = FakeClient()

    report = MODULE.probe(client)

    assert report["ok"] is True
    assert report["stage"] == "conversation-init"
    assert report["request"]["system_hint"] == "plugin:connector_<redacted>"
    assert report["request"]["user_prompt_sent"] is False
    assert report["request"]["github_tool_invoked"] is False
    assert report["response"]["received"] is True
    assert report["response"]["top_level_keys"] == [
        "conversation_id",
        "default_model_slug",
        "some_metadata",
    ]


def test_probe_does_not_expose_connector_or_conversation_identifiers() -> None:
    client = FakeClient()

    report = MODULE.probe(client)
    rendered = str(report)

    assert "connector_test" not in rendered
    assert "conversation_secret" not in rendered
    assert [path for _, path, _ in client.calls] == [
        "/ps/plugins/installed?limit=1000",
        "/apps/availability?platform=chat&locale=en-US",
        "/conversation/init",
    ]
