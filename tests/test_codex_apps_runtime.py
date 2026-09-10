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


def test_progress_reporter_rolls_up_tool_calls_and_stays_quiet():
    import io

    from speckit_powerpack.codex_apps_runtime import make_progress_reporter

    out = io.StringIO()
    report = make_progress_reporter("review", out)

    report({"kind": "event", "event": {"type": "turn.started"}})
    report({"kind": "event", "event": {"type": "thread.started"}})  # dedup — no second line
    # 50 completed fetch_file calls must NOT produce 50 lines
    for i in range(50):
        report({"kind": "event", "event": {"item": {
            "id": f"call-{i}", "type": "mcp_tool_call", "server": "codex_apps",
            "tool": "github.fetch_file", "status": "completed",
        }}})
    report({"kind": "heartbeat", "elapsed": 120.0})   # forces one summary
    report({"kind": "event", "event": {"item": {"type": "web_search"}}})
    report({"kind": "event", "event": {"item": {"type": "agent_message", "text": "x"}}})
    report({"kind": "event", "event": {"type": "turn.completed"}})

    lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
    assert sum("codex turn started" in ln for ln in lines) == 1
    assert any("50 GitHub calls" in ln and "fetch_file×50" in ln for ln in lines)
    assert any("web search attempted (rejected" in ln for ln in lines)
    assert any("drafting the review verdict" in ln for ln in lines)
    assert lines[-1] == "  [review] ✓ turn completed"
    assert len(lines) <= 8  # rolled up, not one line per call


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
