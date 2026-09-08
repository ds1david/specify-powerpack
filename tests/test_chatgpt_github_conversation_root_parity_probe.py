from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_conversation_root_parity.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_conversation_root_parity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_prepare_body_uses_client_created_root_without_partial_id_by_default() -> None:
    body = MODULE._prepare_body(
        connector_id="connector_test",
        model="gpt-5-6-thinking",
        partial_query="GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
        include_partial_query_id=False,
    )

    assert body["parent_message_id"] == "client-created-root"
    assert "id" not in body["partial_query"]
    assert body["thinking_effort"] == "extended"
    assert body["system_hints"] == ["plugin:connector_test"]


def test_prepare_body_can_add_har_observed_partial_query_id() -> None:
    body = MODULE._prepare_body(
        connector_id="connector_test",
        model="gpt-5-6-thinking",
        partial_query="GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
        include_partial_query_id=True,
    )

    assert body["parent_message_id"] == "client-created-root"
    assert isinstance(body["partial_query"]["id"], str)
    assert body["partial_query"]["id"]


def test_submit_body_preserves_root_and_structured_github_mention() -> None:
    body = MODULE._submit_body(
        connector_id="connector_test",
        model="gpt-5-6-thinking",
        prompt="@GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        prepare_state="success",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
    )

    assert body["parent_message_id"] == "client-created-root"
    assert body["system_hints"] == ["plugin:connector_test"]
    message = body["messages"][0]
    offset = message["metadata"]["serialization_metadata"]["custom_symbol_offsets"][0]
    assert offset == {
        "id": "plugin:connector_test",
        "symbol": "ecosystemMention",
        "startIndex": 0,
        "endIndex": 7,
    }
    assert body["thinking_effort"] == "extended"
