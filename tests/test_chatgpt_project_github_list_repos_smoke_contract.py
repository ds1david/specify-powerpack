from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SMOKE = ROOT / "scripts" / "homologation" / "smoke_chatgpt_project_github_list_repos.py"
PROJECT_CONTEXT = (
    "CHATGPT PROJECT: Projeto Exemplo\n\n"
    "PROJECT METADATA / INSTRUCTIONS:\n"
    "description: Laboratório de estratégias autônomas com gestão de risco e observabilidade."
)


def _load():
    spec = importlib.util.spec_from_file_location("smoke_chatgpt_project_github_list_repos", SMOKE)
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
                "tool": "github.list_repositories",
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
                "tool": "github.list_repositories",
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
                    "PROJECT_NAME: Projeto Exemplo\n"
                    "PROJECT_DESCRIPTION: Laboratório para evolução de estratégias autônomas com gestão de risco e observabilidade.\n"
                    "PROJECT_CONTEXT_EVIDENCE: estratégias autônomas com gestão de risco e observabilidade\n"
                    "REPO ds1david/repo-a\n"
                    "REPO ds1david/repo-b\n"
                    "TOTAL 2\n"
                    "POWERPACK_PROJECT_GITHUB_OK"
                ),
            },
        },
        {"type": "turn.completed", "usage": {}},
    ]
    return "\n".join(json.dumps(event) for event in events)


def _fake_github_state():
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

    return FakeGitHubState()


def _fake_client():
    class FakeClient:
        def build_project_context(self, project_id, *, max_conversations, max_chars):
            assert project_id == "g-p-test123"
            assert max_conversations == 2
            assert max_chars == 20000
            return SimpleNamespace(id="g-p-test123", name="Projeto Exemplo"), PROJECT_CONTEXT

    return FakeClient()


def _args(tmp_path: Path, *, include_repositories: bool = False, include_assistant_text: bool = False):
    return SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        locale="pt-BR",
        max_conversations=2,
        timeout=300,
        include_repositories=include_repositories,
        include_assistant_text=include_assistant_text,
    )


def test_smoke_combines_project_context_and_explicit_github_app() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    folded = text.casefold()
    assert "load_project_binding" in text
    assert "build_project_context" in text
    assert "[$github](app://{connector_id})" in text
    assert "run_codex_exec" in text
    assert "PROJECT_DESCRIPTION" in text
    assert "PROJECT_CONTEXT_EVIDENCE" in text
    assert '"browser_used": false' in folded
    assert '"project_context_serialized": true' in folded
    assert '"native_project_binding": false' in folded
    assert '"explicit_app_mention": true' in folded


def test_prompt_requires_project_name_description_literal_evidence_and_all_github_repositories() -> None:
    module = _load()
    prompt = module._build_prompt(
        connector_id="connector_github_test",
        project_context=PROJECT_CONTEXT,
    )
    assert "[$github](app://connector_github_test)" in prompt
    assert "nome exato do ChatGPT Project" in prompt
    assert "descrição abreviada / principal missão" in prompt
    assert "evidência textual curta" in prompt
    assert "literalmente presente" in prompt
    assert "Liste TODOS os repositórios" in prompt
    assert "PROJECT_NAME:" in prompt
    assert "PROJECT_DESCRIPTION:" in prompt
    assert "PROJECT_CONTEXT_EVIDENCE:" in prompt
    assert "REPO owner/name" in prompt
    assert "TOTAL N" in prompt
    assert module.MARKER in prompt
    assert "Não execute comandos shell" in prompt
    assert "Não use web search" in prompt


def test_combined_parser_requires_project_description_evidence_and_consistent_repo_total() -> None:
    module = _load()
    parsed = module._parse_response(
        "PROJECT_NAME: Projeto Exemplo\n"
        "PROJECT_DESCRIPTION: Laboratório de estratégias autônomas com gestão de risco e observabilidade.\n"
        "PROJECT_CONTEXT_EVIDENCE: estratégias autônomas com gestão de risco e observabilidade\n"
        "REPO ds1david/repo-a\n"
        "REPO ds1david/repo-b\n"
        "TOTAL 2\n"
        "POWERPACK_PROJECT_GITHUB_OK"
    )
    assert parsed["project_name"] == "Projeto Exemplo"
    assert parsed["description_present"] is True
    assert parsed["description_max_100_words"] is True
    assert parsed["context_evidence_present"] is True
    assert parsed["context_evidence_length_valid"] is True
    assert parsed["repo_count"] == 2
    assert parsed["duplicate_repo_lines"] == 0
    assert parsed["total_matches_unique_repo_count"] is True
    assert parsed["marker_seen"] is True


def test_run_passes_only_when_project_context_and_github_tool_both_work(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: _fake_client())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: _fake_github_state())
    monkeypatch.setattr(
        module,
        "run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(
            ["codex"],
            0,
            stdout=_success_jsonl(),
            stderr="",
        ),
    )

    report = module.run(_args(tmp_path, include_repositories=True, include_assistant_text=True))

    assert report["ok"] is True
    assert report["classification"] == "CHATGPT_PROJECT_GITHUB_LIST_REPOS_SMOKE_PASSED"
    project_context = report["evidence"]["project_context"]
    assert project_context["project_name_exact_match"] is True
    assert project_context["description_present"] is True
    assert project_context["description_max_100_words"] is True
    assert project_context["context_evidence_in_serialized_context"] is True
    assert project_context["context_evidence_distinct_from_name"] is True
    assert project_context["project_context_contract_passed"] is True
    assert "estratégias autônomas" in project_context["project_description_returned"]
    runtime = report["evidence"]["github_codex_runtime"]
    assert runtime["github_tool_call_observed"] is True
    assert runtime["github_tool_result_observed"] is True
    assert runtime["github_identity_in_event"] is True
    assert report["evidence"]["repository_listing"]["format_contract_passed"] is True
    assert report["evidence"]["no_local_shell_fallback"] is True
    assert report["evidence"]["no_web_search_fallback"] is True
    assert report["repositories"] == ["ds1david/repo-a", "ds1david/repo-b"]
    assert report["timing"]["steps"]


def test_run_fails_if_project_name_is_wrong_even_when_github_succeeds(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)
    broken = _success_jsonl().replace("PROJECT_NAME: Projeto Exemplo", "PROJECT_NAME: Projeto Errado")

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: _fake_client())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: _fake_github_state())
    monkeypatch.setattr(
        module,
        "run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=broken, stderr=""),
    )
    report = module.run(_args(tmp_path))
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_PROJECT_GITHUB_PROJECT_CONTEXT_FAILED"


def test_run_fails_if_description_is_missing_even_when_github_succeeds(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)
    broken = _success_jsonl().replace(
        "PROJECT_DESCRIPTION: Laboratório para evolução de estratégias autônomas com gestão de risco e observabilidade.\n",
        "",
    )

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: _fake_client())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: _fake_github_state())
    monkeypatch.setattr(
        module,
        "run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=broken, stderr=""),
    )
    report = module.run(_args(tmp_path))
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_PROJECT_GITHUB_PROJECT_CONTEXT_FAILED"


def test_run_fails_if_literal_context_evidence_is_not_in_serialized_project(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)
    broken = _success_jsonl().replace(
        "PROJECT_CONTEXT_EVIDENCE: estratégias autônomas com gestão de risco e observabilidade",
        "PROJECT_CONTEXT_EVIDENCE: frase inventada que não existe no contexto serializado",
    )

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: _fake_client())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: _fake_github_state())
    monkeypatch.setattr(
        module,
        "run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=broken, stderr=""),
    )
    report = module.run(_args(tmp_path))
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_PROJECT_GITHUB_PROJECT_CONTEXT_FAILED"
    assert report["evidence"]["project_context"]["context_evidence_in_serialized_context"] is False


def test_run_fails_on_shell_fallback_even_if_project_and_github_output_look_valid(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    shell_event = json.dumps(
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
    raw = _success_jsonl() + "\n" + shell_event

    monkeypatch.setattr(module, "ChatGPTBackendClient", lambda: _fake_client())
    monkeypatch.setattr(module, "discover_github_connector", lambda client, *, locale: _fake_github_state())
    monkeypatch.setattr(
        module,
        "run_codex_exec",
        lambda **kwargs: subprocess.CompletedProcess(["codex"], 0, stdout=raw, stderr=""),
    )
    report = module.run(_args(tmp_path))
    assert report["ok"] is False
    assert report["classification"] == "CHATGPT_PROJECT_GITHUB_FALLBACK_DETECTED"
