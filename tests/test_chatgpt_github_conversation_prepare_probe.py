from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_conversation_prepare.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_conversation_prepare", SCRIPT)
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
                        "status": "ENABLED",
                        "enabled": True,
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
            assert body["system_hints"] == ["plugin:connector_test"]
            return {
                "default_model_slug": "gpt-test",
                "type": "conversation_init",
            }
        if path == "/f/conversation/prepare":
            assert body["model"] == "gpt-test"
            assert body["conversation_mode"] == {"kind": "primary_assistant"}
            assert body["system_hints"] == ["plugin:connector_test"]
            assert body["partial_query"]["content"]["parts"] == ["GitHub LISTE TODOS OS MEUS REPOSITORIOS"]
            assert body["parent_message_id"]
            return {
                "conduit_token": "super-secret-conduit-token",
                "some_public_field": "ok",
            }
        raise AssertionError(path)


def test_prepare_probe_uses_har_observed_sequence_and_redacts_transient_ids() -> None:
    client = FakeClient()

    report = MODULE.probe(client)

    assert report["ok"] is True
    assert report["stage"] == "conversation-prepare"
    assert report["request"]["system_hint"] == "plugin:connector_<redacted>"
    assert report["request"]["final_user_message_sent"] is False
    assert report["request"]["github_tool_invoked"] is False
    assert report["response"]["conduit_token_present"] is True
    assert report["response"]["conduit_token_exposed"] is False
    assert [path for _, path, _ in client.calls] == [
        "/ps/plugins/installed?limit=1000",
        "/apps/availability?platform=chat&locale=en-US",
        "/conversation/init",
        "/f/conversation/prepare",
    ]

    rendered = str(report)
    assert "connector_test" not in rendered
    assert "super-secret-conduit-token" not in rendered
    assert "plugin_connector_1p_test" not in rendered


def test_prepare_probe_fails_closed_when_conduit_token_is_absent() -> None:
    class NoConduitClient(FakeClient):
        def request_json(self, method: str, path: str, body=None):
            if path == "/f/conversation/prepare":
                self.calls.append((method, path, body))
                return {"some_public_field": "ok"}
            return super().request_json(method, path, body)

    report = MODULE.probe(NoConduitClient())

    assert report["ok"] is False
    assert report["response"]["conduit_token_present"] is False
