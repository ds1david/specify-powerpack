from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_conversation_har_shape.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_conversation_har_shape", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_har_shape_submit_body_contains_successful_web_non_secret_fields() -> None:
    body = MODULE._build_har_shape_submit_body(
        connector_id="connector_test",
        model="gpt-5-6-thinking",
        parent_message_id="parent-test",
        prompt="@GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        prepare_state="success",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
        create_time=123.5,
    )

    message = body["messages"][0]
    hint = "plugin:connector_test"

    assert message["create_time"] == 123.5
    assert body["system_hints"] == [hint]
    assert message["metadata"]["system_hints"] == [hint]
    assert message["metadata"]["serialization_metadata"]["custom_symbol_offsets"] == [
        {
            "id": hint,
            "symbol": "ecosystemMention",
            "startIndex": 0,
            "endIndex": 7,
        }
    ]
    assert body["model_response_contracts"] == MODULE.MODEL_RESPONSE_CONTRACTS
    assert body["client_contextual_info"]["app_name"] == "chatgpt.com"
    assert body["paragen_cot_summary_display_override"] == "allow"
    assert body["force_parallel_switch"] == "auto"
    assert body["thinking_effort"] == "extended"
    assert body["local_function_names"] == ["local.continue_in_work"]
    assert body["supported_encodings"] == ["v1"]


def test_har_shape_omits_unproven_thinking_effort_for_other_models() -> None:
    body = MODULE._build_har_shape_submit_body(
        connector_id="connector_test",
        model="gpt-other",
        parent_message_id="parent-test",
        prompt="@GitHub test",
        prepare_state="success",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
        create_time=1.0,
    )

    assert "thinking_effort" not in body


def test_base_client_context_contains_no_session_identifiers() -> None:
    context = MODULE._base_client_context()

    assert context == {
        "app_name": "chatgpt.com",
        "has_web_push_capabilities": False,
        "web_push_notification_permission": "default",
    }
    rendered = str(context).casefold()
    assert "token" not in rendered
    assert "cookie" not in rendered
    assert "session" not in rendered
