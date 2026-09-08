from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "probe_chatgpt_github_conversation_submit.py"
SPEC = importlib.util.spec_from_file_location("probe_chatgpt_github_conversation_submit", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_submit_body_materializes_github_mention_and_connector_metadata() -> None:
    body = MODULE._build_submit_body(
        connector_id="connector_test",
        model="gpt-test",
        parent_message_id="parent-test",
        prompt="@GitHub LISTE TODOS OS MEUS REPOSITORIOS",
        prepare_state="success",
        timezone="America/Sao_Paulo",
        timezone_offset_min=180,
    )

    hint = "plugin:connector_test"
    message = body["messages"][0]
    assert body["system_hints"] == [hint]
    assert message["metadata"]["system_hints"] == [hint]
    assert message["content"]["parts"][0].startswith("@GitHub")
    offset = message["metadata"]["serialization_metadata"]["custom_symbol_offsets"][0]
    assert offset == {
        "id": hint,
        "symbol": "ecosystemMention",
        "startIndex": 0,
        "endIndex": 7,
    }
    assert body["client_prepare_state"] == "success"


def test_sse_inspection_requires_structural_github_tool_evidence_not_text_only() -> None:
    lines = [
        'data: {"type":"message","message":{"author":{"role":"assistant"},"content":"GitHub mentioned only"}}',
        'data: {"type":"message","message":{"author":{"role":"tool","name":"github"},"content":{"content_type":"execution_output"}}}',
        'data: {"type":"delta","delta":"POWERPACK_GITHUB_TOOL_OK"}',
        'data: [DONE]',
    ]

    report = MODULE._inspect_sse_lines(lines)

    assert report["event_count"] == 3
    assert report["assistant_text_seen"] is True
    assert report["marker_seen"] is True
    assert report["structural_github_tool_evidence"] is True
    assert report["event_types"] == {"message": 2, "delta": 1}
