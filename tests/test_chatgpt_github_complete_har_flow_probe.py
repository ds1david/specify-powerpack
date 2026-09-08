from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_complete_har_flow.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_complete_har_flow", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_complete_har_flow_preserves_observed_unresolved_then_connector_sequence() -> None:
    prompt = "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK"

    unresolved = MODULE._unresolved_prepare_body(
        prompt=prompt,
        model=MODULE.HAR_MODEL,
        thinking_effort=MODULE.HAR_THINKING_EFFORT,
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
    )
    connector = MODULE._connector_prepare_body(
        connector_id="connector_test",
        prompt=prompt,
        model=MODULE.HAR_MODEL,
        thinking_effort=MODULE.HAR_THINKING_EFFORT,
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
    )

    assert unresolved["system_hints"] == []
    assert unresolved["client_prepare_state"] == "none"
    assert unresolved["client_prepare_dispatch"] == "debounced"
    assert unresolved["client_prepare_source"] == "composer_editor_state"
    assert unresolved["partial_query"]["content"]["parts"][0].startswith("@GitHub")
    assert unresolved["conversation_origin"] == "tpp"
    assert unresolved["model"] == "gpt-5.6-sol-wm"
    assert unresolved["thinking_effort"] == "xhigh"

    assert connector["system_hints"] == ["plugin:connector_test"]
    assert connector["client_prepare_state"] == "sent"
    assert connector["client_prepare_dispatch"] == "immediate"
    assert connector["client_prepare_source"] == "context_change"
    assert connector["partial_query"]["content"]["parts"][0].startswith("GitHub ")
    assert not connector["partial_query"]["content"]["parts"][0].startswith("@GitHub")


def test_final_submit_uses_success_not_prepare_http_status_ok() -> None:
    prompt = "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM POWERPACK_GITHUB_TOOL_OK"

    body = MODULE._final_submit_body(
        connector_id="connector_test",
        prompt=prompt,
        model=MODULE.HAR_MODEL,
        thinking_effort=MODULE.HAR_THINKING_EFFORT,
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
        create_time=123.0,
    )

    assert body["client_prepare_state"] == "success"
    assert body["conversation_origin"] == "tpp"
    assert body["model"] == "gpt-5.6-sol-wm"
    assert body["thinking_effort"] == "xhigh"
    assert body["parent_message_id"] == "client-created-root"
    assert body["system_hints"] == ["plugin:connector_test"]
    message = body["messages"][0]
    assert message["content"]["parts"][0] == prompt
    assert message["metadata"]["system_hints"] == ["plugin:connector_test"]
    offset = message["metadata"]["serialization_metadata"]["custom_symbol_offsets"][0]
    assert offset == {
        "id": "plugin:connector_test",
        "symbol": "ecosystemMention",
        "startIndex": 0,
        "endIndex": 7,
    }


def test_handoff_inspection_never_exposes_resume_token_values() -> None:
    lines = [
        'data: {"type":"resume_conversation_token","token":"secret","conversation_id":"conv-test"}',
        'data: {"type":"stream_handoff","conversation_id":"conv-test","turn_exchange_id":"turn-test"}',
        'data: [DONE]',
    ]

    report = MODULE._inspect_handoff(lines)

    assert report == {
        "event_count": 2,
        "resume_conversation_token_seen": True,
        "stream_handoff_seen": True,
        "conversation_id_present": True,
        "turn_exchange_id_present": True,
        "token_values_exposed": False,
    }
    assert "secret" not in str(report)
