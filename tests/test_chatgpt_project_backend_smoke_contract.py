from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SMOKE = ROOT / "scripts" / "homologation" / "smoke_chatgpt_project_backend.py"
HISTORICAL_PROMPT = (
    "me diga qual é o nome do projeto e sua principal missão, produza uma resposta "
    "simplificada de no máximo 100 palavras. e me responda quanto é 1 +1"
)


def _load():
    spec = importlib.util.spec_from_file_location("smoke_chatgpt_project_backend", SMOKE)
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
                    "project_url": "https://chatgpt.com/g/g-p-test123/project",
                },
            }
        ),
        encoding="utf-8",
    )


def _args(tmp_path: Path, *, discover_github: bool = False):
    return SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        effort="high",
        max_conversations=2,
        discover_github=discover_github,
        locale="pt-BR",
        include_assistant_text=False,
    )


def test_smoke_reuses_recovered_project_context_prompt() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    assert "PROJECT_CONTEXT_SMOKE_PROMPT" in text
    assert "run_project_review(" in text
    assert "project_id_or_url=binding[\"project_id\"]" in text


def test_smoke_is_strictly_browserless_backend_flow() -> None:
    text = SMOKE.read_text(encoding="utf-8").casefold()

    assert '"transport": "chatgpt-backend-api"' in text
    assert '"browser_used": false' in text
    assert '"cdp_used": false' in text
    assert '"web2api_used": false' in text
    assert "chatgpt-web2api" not in text
    assert "cdpdriver" not in text
    assert "playwright" not in text
    assert "powershell" not in text
    assert "selenium" not in text
    assert "@github" not in text


def test_smoke_requires_existing_repository_project_binding(tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    binding = module._load_binding(tmp_path)
    assert binding["project_id"] == "g-p-test123"
    assert binding["project_name"] == "Projeto Exemplo"
    assert binding["mode"] == "backend-api"
    assert binding["authorization"] == "codex-backend-api"


def test_response_contract_checks_name_arithmetic_and_100_words() -> None:
    module = _load()
    response = (
        "O projeto se chama Projeto Exemplo. Sua principal missão é validar o contexto do Project. "
        "Quanto a 1 + 1, o resultado é 2."
    )
    checks = module._evaluate(response, "Projeto Exemplo")
    assert checks["response_non_empty"] is True
    assert checks["project_name_present"] is True
    assert checks["one_plus_one_equals_two"] is True
    assert checks["max_100_words"] is True


def test_run_calls_existing_project_provider_without_browser(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)
    captured = {}

    def fake_run_project_review(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            provider="chatgpt-project",
            text="Projeto Exemplo tem a missão de validar contexto. 1 + 1 = 2.",
            project_id="g-p-test123",
            project_name="Projeto Exemplo",
            response_id="resp_test",
        )

    monkeypatch.setattr(module, "run_project_review", fake_run_project_review)
    report = module.run(_args(tmp_path))

    assert report["ok"] is True
    assert captured["prompt"] == module.PROJECT_CONTEXT_SMOKE_PROMPT
    assert captured["project_id_or_url"] == "g-p-test123"
    assert report["request"]["browser_used"] is False
    assert report["request"]["cdp_used"] is False
    assert report["request"]["web2api_used"] is False
    assert report["request"]["github_plugin_discovery_requested"] is False
    assert report["evidence"]["github_discovery"] is None


def test_optional_github_discovery_runs_before_same_project_prompt(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)
    order: list[str] = []

    class FakeGithubState:
        def safe_report(self):
            return {
                "ok": True,
                "github_plugin": {"resolved": True, "status": "ENABLED"},
                "authorization": {"auth_status": "ACTIVE"},
                "availability": {"installed": True, "available": True},
                "raw_secrets_included": False,
            }

    def fake_discover(client, *, locale):
        order.append(f"github:{locale}")
        return FakeGithubState()

    def fake_run_project_review(**kwargs):
        order.append("project-review")
        return SimpleNamespace(
            provider="chatgpt-project",
            text="Projeto Exemplo tem a missão de validar contexto. 1 + 1 = 2.",
            project_id="g-p-test123",
            project_name="Projeto Exemplo",
            response_id="resp_test",
        )

    monkeypatch.setattr(module, "discover_github_connector", fake_discover)
    monkeypatch.setattr(module, "run_project_review", fake_run_project_review)

    report = module.run(_args(tmp_path, discover_github=True))

    assert report["ok"] is True
    assert order == ["github:pt-BR", "project-review"]
    assert report["request"]["github_plugin_discovery_requested"] is True
    assert report["request"]["github_plugin_requested_in_prompt"] is False
    assert report["evidence"]["github_discovery"]["ok"] is True
