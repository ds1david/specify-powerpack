from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from speckit_powerpack.chatgpt_project_provider import (
    ChatGPTBackendClient,
    ChatGPTProjectError,
    load_codex_auth,
    project_id_from_url_or_id,
    run_codex_cli_review,
)


def test_load_codex_auth_uses_existing_codex_tokens(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(
        json.dumps({"tokens": {"access_token": "header.payload.signature", "account_id": "acct-test"}}),
        encoding="utf-8",
    )

    result = load_codex_auth(auth)

    assert result.access_token == "header.payload.signature"
    assert result.account_id == "acct-test"
    assert result.auth_path == auth


def test_load_codex_auth_fails_closed_when_token_missing(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"tokens": {"account_id": "acct-test"}}), encoding="utf-8")

    with pytest.raises(ChatGPTProjectError, match="access_token"):
        load_codex_auth(auth)


def test_project_id_is_extracted_from_real_project_style_url() -> None:
    value = "https://chatgpt.com/g/g-p-6a7c9c009cf08191bca56001c8bd1a9f-autonomous-trading-strategy-evolution-lab/project"
    assert project_id_from_url_or_id(value) == "g-p-6a7c9c009cf08191bca56001c8bd1a9f"


def test_project_discovery_parses_nested_sidebar_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"tokens": {"access_token": "t", "account_id": "a"}}), encoding="utf-8")
    client = ChatGPTBackendClient(auth)

    payload = {
        "items": [
            {
                "gizmo": {
                    "id": "g-p-abc123",
                    "display": {"name": "My Project"},
                    "short_url": "g-p-abc123-my-project",
                }
            }
        ]
    }
    monkeypatch.setattr(client, "request_json", lambda method, path, body=None: payload)

    projects = client.list_projects()

    assert len(projects) == 1
    assert projects[0].id == "g-p-abc123"
    assert projects[0].name == "My Project"
    assert projects[0].url.endswith("/g/g-p-abc123-my-project/project")


def test_project_context_contains_instructions_and_recent_conversation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"tokens": {"access_token": "t", "account_id": "a"}}), encoding="utf-8")
    client = ChatGPTBackendClient(auth)

    def request(method: str, path: str, body=None):
        if path == "/gizmos/g-p-abc123":
            return {"id": "g-p-abc123", "name": "Project Alpha", "instructions": "Respect SPEC-001."}
        if path.startswith("/gizmos/g-p-abc123/conversations"):
            return {"items": [{"id": "conv-1", "title": "Previous code review"}]}
        if path == "/conversation/conv-1":
            return {
                "mapping": {
                    "1": {
                        "message": {
                            "author": {"role": "user"},
                            "create_time": 1,
                            "content": {"parts": ["Review the retry contract."]},
                        }
                    },
                    "2": {
                        "message": {
                            "author": {"role": "assistant"},
                            "create_time": 2,
                            "content": {"parts": ["Retries must remain idempotent."]},
                        }
                    },
                }
            }
        raise AssertionError(path)

    monkeypatch.setattr(client, "request_json", request)

    project, context = client.build_project_context("g-p-abc123")

    assert project.name == "Project Alpha"
    assert "Respect SPEC-001" in context
    assert "Previous code review" in context
    assert "Retries must remain idempotent" in context


def test_codex_cli_review_smoke_parses_agent_message(tmp_path: Path) -> None:
    expected = "Finding: guard division by zero.\nPOWERPACK_SMOKE_CLI_OK"

    def fake_runner(argv, **kwargs):
        assert argv[:3] == ["codex", "exec", "--json"]
        assert "--sandbox" in argv
        assert "read-only" in argv
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps({"item": {"type": "agent_message", "text": expected}}) + "\n",
            stderr="",
        )

    result = run_codex_cli_review(prompt="review", cwd=tmp_path, runner=fake_runner)

    assert result.provider == "codex"
    assert "POWERPACK_SMOKE_CLI_OK" in result.text
