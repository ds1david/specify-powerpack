from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SMOKE = ROOT / "scripts" / "homologation" / "smoke_chatgpt_github_list_repos_codex_apps.py"


def _load():
    spec = importlib.util.spec_from_file_location("smoke_chatgpt_github_list_repos_codex_apps", SMOKE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _success_jsonl() -> str:
    events = [
        {"type": "thread.started", "thread_id": "thread-1"},
        {"type": "turn.started"},
        {
            "type": "item.started",
            "item": {
                "id": "mcp-1",
                "type": "mcp_tool_call",
                "server": "codex_apps",
                "tool": "github.list_repos",
                "arguments": {},
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
                "tool": "github.list_repos",
                "arguments": {},
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "ds1david/repo-a\nds1david/repo-b",
                        }
                    ]
                },
                "error": None,
                "status": "completed",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "msg-1",
                "type": "agent_message",
                "text": (
                    "REPO ds1david/repo-a\n"
                    "REPO ds1david/repo-b\n"
                    "TOTAL 2\n"
                    "POWERPACK_GITHUB_LIST_REPOS_OK"
                ),
            },
        },
        {"type": "turn.completed", "usage": {}},
    ]
    return "\n".join(json.dumps(event) for event in events)


def test_smoke_is_browserless_codex_apps_only() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    folded = text.casefold()

    assert "liste todos os meus repositorios" in folded
    assert "[$github](app://{connector_id})" in text
    assert '"browser_used": false' in folded
    assert '"cdp_used": false' in folded
    assert '"web2api_used": false' in folded
    assert '"direct_codex_responses_submit_used": false' in folded
    assert '"project_context_used": false' in folded
    assert "speckit_powerpack.codex_apps_smoke_runtime" in text
    assert "from smoke_chatgpt_github_codex_apps import" not in text
    assert "/backend-api/codex/responses" not in folded
    assert "/backend-api/f/conversation" not in folded
    assert "plugin:connector_" not in folded
    assert "cdpdriver" not in folded
    assert "chatgpt-web2api" not in folded
    assert "playwright" not in folded
    assert "selenium" not in folded


def test_prompt_explicitly_selects_github_and_requires_all_pages() -> None:
    module = _load()
    prompt = module._build_prompt(connector_id="connector_test")

    assert prompt.startswith(module.BASE_PROMPT)
    assert "[$github](app://connector_test)" in prompt
    assert "TODOS os repositórios" in prompt
    assert "continue consultando páginas" in prompt
    assert "Não execute comandos shell" in prompt
    assert "Não use web search" in prompt
    assert "Não use outro app/connector" in prompt
    assert "REPO owner/name" in prompt
    assert "TOTAL N" in prompt
    assert module.MARKER in prompt


def test_repo_listing_parser_requires_unique_lines_and_matching_total() -> None:
    module = _load()
    listing = module._parse_repo_listing(
        "REPO ds1david/repo-a\nREPO ds1david/repo-b\nTOTAL 2\nPOWERPACK_GITHUB_LIST_REPOS_OK"
    )
    assert listing["repos"] == ["ds1david/repo-a", "ds1david/repo-b"]
    assert listing["repo_count"] == 2
    assert listing["duplicate_repo_lines"] == 0
    assert listing["declared_total"] == 2
    assert listing["total_present"] is True
    assert listing["total_matches_unique_repo_count"] is True


def test_repo_listing_parser_detects_duplicate_or_mismatched_total() -> None:
    module = _load()
    listing = module._parse_repo_listing(
        "REPO ds1david/repo-a\nREPO ds1david/repo-a\nTOTAL 2\nPOWERPACK_GITHUB_LIST_REPOS_OK"
    )
    assert listing["repo_count"] == 1
    assert listing["duplicate_repo_lines"] == 1
    assert listing["total_matches_unique_repo_count"] is False


def test_run_passes_only_with_structural_github_tool_result_and_consistent_list(monkeypatch, tmp_path: Path) -> None:
    module = _load()

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

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: object())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: FakeGitHubState())
    monkeypatch.setattr(
        module,
        "_run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(
            ["codex"],
            0,
            stdout=_success_jsonl(),
            stderr="",
        ),
    )

    args = SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        locale="pt-BR",
        timeout=300,
        include_repositories=True,
        include_assistant_text=False,
    )
    report = module.run(args)

    assert report["ok"] is True
    assert report["classification"] == "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_SMOKE_PASSED"
    assert report["request"]["project_context_used"] is False
    assert report["request"]["explicit_app_mention"] is True
    runtime = report["evidence"]["github_codex_runtime"]
    assert runtime["github_tool_call_observed"] is True
    assert runtime["github_tool_result_observed"] is True
    assert runtime["github_identity_in_event"] is True
    listing = report["evidence"]["repository_listing"]
    assert listing["repo_count"] == 2
    assert listing["declared_total"] == 2
    assert listing["format_contract_passed"] is True
    assert report["repositories"] == ["ds1david/repo-a", "ds1david/repo-b"]
    assert report["evidence"]["no_local_shell_fallback"] is True
    assert report["evidence"]["no_web_search_fallback"] is True

    timing = report["timing"]
    assert timing["total_seconds"] >= 0
    assert timing["measured_steps_seconds"] >= 0
    assert [step["name"] for step in timing["steps"]] == [
        "validate_working_directory",
        "initialize_backend_client",
        "github_chat_preflight",
        "build_prompt",
        "codex_exec",
        "parse_codex_jsonl",
        "parse_repository_listing",
        "evaluate_contract",
    ]
    assert all(step["elapsed_seconds"] >= 0 for step in timing["steps"])
    assert all(step["status"] == "ok" for step in timing["steps"])


def test_run_fails_when_final_total_does_not_match(monkeypatch, tmp_path: Path) -> None:
    module = _load()

    class FakeGitHubState:
        ok = True
        connector_id = "connector_github_test"

        def safe_report(self):
            return {"ok": True, "raw_secrets_included": False}

    broken = _success_jsonl().replace("TOTAL 2", "TOTAL 3")
    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: object())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: FakeGitHubState())
    monkeypatch.setattr(
        module,
        "_run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=broken, stderr=""),
    )

    args = SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        locale="pt-BR",
        timeout=300,
        include_repositories=False,
        include_assistant_text=False,
    )
    report = module.run(args)
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_LIST_CONTRACT_FAILED"


def test_run_fails_on_shell_or_web_fallback(monkeypatch, tmp_path: Path) -> None:
    module = _load()

    class FakeGitHubState:
        ok = True
        connector_id = "connector_github_test"

        def safe_report(self):
            return {"ok": True, "raw_secrets_included": False}

    extra = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "id": "cmd",
                "type": "command_execution",
                "command": "gh repo list",
                "aggregated_output": "",
                "exit_code": 0,
                "status": "completed",
            },
        }
    )
    raw = _success_jsonl() + "\n" + extra
    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: object())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: FakeGitHubState())
    monkeypatch.setattr(
        module,
        "_run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=raw, stderr=""),
    )

    args = SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        locale="pt-BR",
        timeout=300,
        include_repositories=False,
        include_assistant_text=False,
    )
    report = module.run(args)
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_FALLBACK_DETECTED"
