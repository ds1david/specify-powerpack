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


def test_format_progress_renders_the_turn_lifecycle():
    from speckit_powerpack.codex_apps_runtime import format_progress as fp

    assert fp({"kind": "event", "event": {"type": "turn.started"}}, phase="review") == "  [review] codex turn started"
    assert fp({"kind": "heartbeat", "elapsed": 63.4}, phase="review") == "  [review] still working… 63s elapsed"
    tool = fp({"kind": "event", "event": {"item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "github.fetch_pr_patch", "status": "completed"}}}, phase="snapshot")
    assert tool == "  [snapshot] · codex_apps.github.fetch_pr_patch [completed]"
    warn = fp({"kind": "event", "event": {"item": {"type": "web_search"}}}, phase="review")
    assert warn is not None and "web search" in warn
    assert fp({"kind": "event", "event": {"type": "turn.completed"}}, phase="review") == "  [review] ✓ turn completed"
    # non-interesting events stay silent
    assert fp({"kind": "event", "event": {"type": "item.updated", "item": {"type": "reasoning_delta"}}}, phase="review") is None


def test_select_project_accepts_id_slug_and_url_forms():
    from speckit_powerpack import cli

    class P:
        def __init__(self, pid, name, url):
            self.id, self.name, self.url = pid, name, url

    projects = [
        P("g-p-6a9ba1a060208191a5b6e03a3950b183", "specify-powerpack", "https://chatgpt.com/g/g-p-6a9ba1a060208191a5b6e03a3950b183-specify-powerpack/project"),
        P("g-p-0000000000000000000000000000abcd", "other", "https://chatgpt.com/g/g-p-0000000000000000000000000000abcd-other/project"),
    ]
    want = projects[0]
    for selector in (
        "g-p-6a9ba1a060208191a5b6e03a3950b183",                                   # bare id
        "g-p-6a9ba1a060208191a5b6e03a3950b183-specify-powerpack",                  # id + slug
        "https://chatgpt.com/g/g-p-6a9ba1a060208191a5b6e03a3950b183-specify-powerpack/project",  # url
        "specify-powerpack",                                                       # exact name
    ):
        assert cli._select_project(projects, selector, None) is want, selector
    with pytest.raises(cli.PowerPackError):
        cli._select_project(projects, "nonexistent", None)
