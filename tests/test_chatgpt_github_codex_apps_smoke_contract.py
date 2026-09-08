from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SMOKE = ROOT / "scripts" / "homologation" / "smoke_chatgpt_github_codex_apps.py"


def _load():
    spec = importlib.util.spec_from_file_location("smoke_chatgpt_github_codex_apps", SMOKE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_binding(tmp_path: Path) -> None:
    review_dir = tmp_path / ".specify" / "powerpack"
    review_dir.mkdir(parents=True)
    (review_dir / "review.json").write_text(
        json.dumps(
            {
                "provider": "chatgpt-project",
                "chatgpt_web": {
                    "mode": "backend-api",
                    "authorization": "codex-backend-api",
                    "project_id": "g-p-test123",
                    "project_name": "Projeto Exemplo",
                },
            }
        ),
        encoding="utf-8",
    )


def _success_jsonl(repo: str) -> str:
    events = [
        {"type": "thread.started", "thread_id": "thread-1"},
        {"type": "turn.started"},
        {
            "type": "item.started",
            "item": {
                "id": "mcp-1",
                "type": "mcp_tool_call",
                "server": "codex_apps",
                "tool": "github_repository_lookup",
                "arguments": {"repo": repo},
                "result": None,
                "error": None,
                "status": "in_progress",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "mcp-1",
                "type": "mcp_tool_call",
                "server": "codex_apps",
                "tool": "github_repository_lookup",
                "arguments": {"repo": repo},
                "result": {"content": [{"type": "text", "text": repo}]},
                "error": None,
                "status": "completed",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "msg-1",
                "type": "agent_message",
                "text": f"GitHub access confirmed. POWERPACK_GITHUB_CONNECTOR_OK {repo}",
            },
        },
        {"type": "turn.completed", "usage": {}},
    ]
    return "\n".join(json.dumps(event) for event in events)


def test_smoke_uses_codex_runtime_and_explicit_app_mention_not_private_submit() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    folded = text.casefold()

    assert "codex" in text
    assert '"exec"' in text
    assert '"--json"' in text
    assert '"--ephemeral"' in text
    assert '"--sandbox"' in text
    assert '"read-only"' in text
    assert "[$github](app://{connector_id})" in text
    assert '"direct_codex_responses_submit_used": false' in folded
    assert '"native_project_binding": false' in folded
    assert '"project_context_serialized": true' in folded

    assert "/backend-api/codex/responses" not in folded
    assert "/backend-api/f/conversation" not in folded
    assert "plugin:connector_" not in folded
    assert "cdpdriver" not in folded
    assert "chatgpt-web2api" not in folded
    assert "playwright" not in folded
    assert "selenium" not in folded
    assert "powershell" not in folded


def test_prompt_binds_exact_connector_and_forbids_fallback() -> None:
    module = _load()
    prompt = module._build_prompt(
        connector_id="connector_test",
        repo_full_name="owner/repo",
        project_context="Projeto Exemplo",
    )

    assert "[$github](app://connector_test)" in prompt
    assert "owner/repo" in prompt
    assert module.MARKER in prompt
    assert "Do NOT run shell commands" in prompt
    assert "Do NOT use web search" in prompt
    assert "Do NOT use any other app/connector" in prompt
    assert "NOT a native Project binding" in prompt


def test_jsonl_parser_requires_structural_codex_apps_call() -> None:
    module = _load()
    parsed = module._parse_codex_jsonl(
        _success_jsonl("owner/repo"),
        connector_id="connector_test",
    )

    assert parsed["turn_completed"] is True
    assert parsed["turn_failed"] is False
    assert parsed["codex_apps_call_count"] == 2
    assert parsed["codex_apps_completed_call_count"] == 1
    assert parsed["codex_apps_result_call_count"] == 1
    assert parsed["command_execution_count"] == 0
    assert parsed["web_search_count"] == 0
    assert "github_repository_lookup" in parsed["codex_apps_tools"]
    assert "POWERPACK_GITHUB_CONNECTOR_OK owner/repo" in parsed["assistant_text"]


def test_jsonl_parser_detects_local_or_web_fallback() -> None:
    module = _load()
    events = [
        {
            "type": "item.completed",
            "item": {
                "id": "cmd",
                "type": "command_execution",
                "command": "git remote -v",
                "aggregated_output": "",
                "exit_code": 0,
                "status": "completed",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "web",
                "type": "web_search",
                "query": "owner repo github",
                "action": {},
            },
        },
    ]
    parsed = module._parse_codex_jsonl(
        "\n".join(json.dumps(event) for event in events),
        connector_id="connector_test",
    )
    assert parsed["command_execution_count"] == 1
    assert parsed["web_search_count"] == 1


def test_codex_exec_command_is_ephemeral_json_read_only(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    captured = {}

    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else None)

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module._run_codex_exec(
        project_path=tmp_path,
        model="gpt-5.6-sol",
        prompt="prompt",
        timeout=60,
    )

    command = captured["command"]
    assert command[:3] == ["/usr/bin/codex", "exec", "--json"]
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("-C") + 1] == str(tmp_path)
    assert command[command.index("-m") + 1] == "gpt-5.6-sol"
    assert command[-1] == "prompt"


def test_run_passes_only_with_github_discovery_codex_apps_tool_and_result(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    class FakeGitHubState:
        ok = True
        connector_id = "connector_github_test"

        def safe_report(self):
            return {
                "ok": True,
                "github_plugin": {"resolved": True, "status": "ENABLED"},
                "authorization": {"auth_status": "ACTIVE"},
                "availability": {"installed": True, "available": True},
                "raw_secrets_included": False,
            }

    class FakeClient:
        def build_project_context(self, project_id, *, max_conversations, max_chars):
            assert project_id == "g-p-test123"
            assert max_conversations == 2
            assert max_chars == 16000
            return SimpleNamespace(id="g-p-test123", name="Projeto Exemplo"), "contexto serializado"

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: FakeClient())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: FakeGitHubState())
    monkeypatch.setattr(module, "_github_repo_from_origin", lambda path: "owner/repo")
    monkeypatch.setattr(
        module,
        "_run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(
            ["codex"],
            0,
            stdout=_success_jsonl("owner/repo"),
            stderr="",
        ),
    )

    args = SimpleNamespace(
        path=str(tmp_path),
        github_repo="",
        model="gpt-5.6-sol",
        max_conversations=2,
        locale="pt-BR",
        timeout=300,
        include_assistant_text=False,
    )
    report = module.run(args)

    assert report["ok"] is True
    assert report["classification"] == "CHATGPT_GITHUB_CODEX_APPS_SMOKE_PASSED"
    assert report["request"]["browser_used"] is False
    assert report["request"]["native_project_binding"] is False
    assert report["request"]["project_context_serialized"] is True
    assert report["request"]["direct_codex_responses_submit_used"] is False
    runtime = report["evidence"]["github_codex_runtime"]
    assert runtime["explicit_app_mention_bound"] is True
    assert runtime["github_tool_call_observed"] is True
    assert runtime["github_tool_result_observed"] is True
    assert report["evidence"]["no_local_shell_fallback"] is True
    assert report["evidence"]["no_web_search_fallback"] is True


def test_run_fails_if_codex_uses_shell_even_if_marker_is_present(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    class FakeGitHubState:
        ok = True
        connector_id = "connector_github_test"

        def safe_report(self):
            return {"ok": True, "raw_secrets_included": False}

    class FakeClient:
        def build_project_context(self, project_id, *, max_conversations, max_chars):
            return SimpleNamespace(id="g-p-test123", name="Projeto Exemplo"), "contexto"

    raw = _success_jsonl("owner/repo") + "\n" + json.dumps(
        {
            "type": "item.completed",
            "item": {
                "id": "cmd",
                "type": "command_execution",
                "command": "git status",
                "aggregated_output": "",
                "exit_code": 0,
                "status": "completed",
            },
        }
    )

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: FakeClient())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: FakeGitHubState())
    monkeypatch.setattr(module, "_github_repo_from_origin", lambda path: "owner/repo")
    monkeypatch.setattr(
        module,
        "_run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=raw, stderr=""),
    )

    args = SimpleNamespace(
        path=str(tmp_path),
        github_repo="",
        model="gpt-5.6-sol",
        max_conversations=2,
        locale="pt-BR",
        timeout=300,
        include_assistant_text=False,
    )
    report = module.run(args)
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_GITHUB_CODEX_APPS_FALLBACK_DETECTED"
