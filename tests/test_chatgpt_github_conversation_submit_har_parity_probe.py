from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_conversation_submit_har_parity.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_conversation_submit_har_parity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_har_parity_body_contains_observed_non_secret_fields() -> None:
    body = MODULE._build_har_parity_body(
        connector_id="connector_test",
        model="gpt-test",
        parent_message_id="parent-test",
        prompt="@GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        prepare_state="success",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
    )

    message = body["messages"][0]
    assert isinstance(message["create_time"], float)
    assert body["model_response_contracts"] == [
        {
            "id": "photo_upload_action.v1",
            "protocol_version": 1,
            "presets": ["cap:image", "cap:file", "placement:end"],
        }
    ]
    assert body["client_contextual_info"]["app_name"] == "chatgpt.com"
    assert body["paragen_cot_summary_display_override"] == "allow"
    assert body["force_parallel_switch"] == "auto"
    assert body["thinking_effort"] == "extended"
    assert body["local_function_names"] == ["local.continue_in_work"]
    assert body["client_prepare_state"] == "success"
    assert body["system_hints"] == ["plugin:connector_test"]


def test_har_parity_body_preserves_structured_github_mention() -> None:
    body = MODULE._build_har_parity_body(
        connector_id="connector_test",
        model="gpt-test",
        parent_message_id="parent-test",
        prompt="@GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        prepare_state="success",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
    )

    message = body["messages"][0]
    offset = message["metadata"]["serialization_metadata"]["custom_symbol_offsets"][0]
    assert message["metadata"]["system_hints"] == ["plugin:connector_test"]
    assert offset == {
        "id": "plugin:connector_test",
        "symbol": "ecosystemMention",
        "startIndex": 0,
        "endIndex": 7,
    }
