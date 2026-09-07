from __future__ import annotations

import json
from pathlib import Path

import pytest

# Importing the no-browser entrypoint installs the backend compatibility shims
# used by the real CLI.
from speckit_powerpack import entrypoint_nobrowser  # noqa: F401
from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient


def test_project_discovery_clamps_sidebar_limit_to_backend_max(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(
        json.dumps({"tokens": {"access_token": "token", "account_id": "account"}}),
        encoding="utf-8",
    )
    client = ChatGPTBackendClient(auth)
    requested_paths: list[str] = []

    def request_json(method: str, path: str, body=None):
        requested_paths.append(path)
        return {"items": []}

    monkeypatch.setattr(client, "request_json", request_json)

    assert client.list_projects(limit=100) == []
    assert requested_paths == ["/gizmos/snorlax/sidebar?limit=50"]
