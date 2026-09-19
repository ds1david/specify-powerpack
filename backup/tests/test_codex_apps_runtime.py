from __future__ import annotations

import json

import pytest

from speckit_powerpack.codex_apps_runtime import CodexAppsError, parse_codex_jsonl, require_github_tool_evidence


def _events(*, shell: bool = False) -> str:
    rows = [
        {"type": "turn.started"},
        {"type": "item.started", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "github.get_pr", "status": "in_progress", "result": None, "error": None}},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "github.get_pr", "status": "completed", "result": {"ok": True}, "error": None}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "{}"}},
        {"type": "turn.completed"},
    ]
    if shell:
        rows.insert(2, {"type": "item.completed", "item": {"type": "command_execution", "command": "git diff", "status": "completed"}})
    return "\n".join(json.dumps(row) for row in rows)


def test_runtime_accepts_structural_github_mcp_evidence():
    parsed = parse_codex_jsonl(_events(), connector_id="connector_test")
    assert parsed["codex_apps_completed_call_count"] == 1
    assert parsed["codex_apps_result_call_count"] == 1
    assert parsed["github_identity_in_event"] is True
    require_github_tool_evidence(parsed)


def test_runtime_rejects_shell_fallback_even_with_github_result():
    parsed = parse_codex_jsonl(_events(shell=True), connector_id="connector_test")
    with pytest.raises(CodexAppsError, match="shell fallback"):
        require_github_tool_evidence(parsed)
