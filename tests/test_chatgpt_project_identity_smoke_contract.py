from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SMOKE = ROOT / "scripts" / "homologation" / "smoke_chatgpt_project_identity.py"


def _load():
    spec = importlib.util.spec_from_file_location("smoke_chatgpt_project_identity", SMOKE)
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


def test_smoke_is_browserless_and_requires_bound_project() -> None:
    text = SMOKE.read_text(encoding="utf-8")
    folded = text.casefold()
    assert "load_project_binding" in text
    assert "run_project_review" in text
    assert '"browser_used": false' in folded
    assert '"cdp_used": false' in folded
    assert '"web2api_used": false' in folded
    assert '"project_context_serialized": true' in folded
    assert '"native_project_binding": false' in folded


def test_prompt_asks_name_and_description_max_100_words() -> None:
    module = _load()
    assert "nome do ChatGPT Project" in module.PROMPT
    assert "no máximo 100 palavras" in module.PROMPT
    assert "PROJECT_NAME:" in module.PROMPT
    assert "PROJECT_DESCRIPTION:" in module.PROMPT
    assert module.MARKER in module.PROMPT


def test_parser_enforces_description_word_limit() -> None:
    module = _load()
    parsed = module._parse_response(
        "PROJECT_NAME: Projeto Exemplo\n"
        "PROJECT_DESCRIPTION: Um projeto curto para validar contexto.\n"
        "POWERPACK_PROJECT_CONTEXT_OK"
    )
    assert parsed["project_name"] == "Projeto Exemplo"
    assert parsed["description_present"] is True
    assert parsed["description_max_100_words"] is True
    assert parsed["marker_seen"] is True

    too_long = " ".join(["palavra"] * 101)
    parsed_long = module._parse_response(
        f"PROJECT_NAME: Projeto Exemplo\nPROJECT_DESCRIPTION: {too_long}\nPOWERPACK_PROJECT_CONTEXT_OK"
    )
    assert parsed_long["description_word_count"] == 101
    assert parsed_long["description_max_100_words"] is False


def test_run_passes_only_when_project_name_matches_binding(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    def fake_review(**kwargs):
        assert kwargs["project_id_or_url"] == "g-p-test123"
        return SimpleNamespace(
            text=(
                "PROJECT_NAME: Projeto Exemplo\n"
                "PROJECT_DESCRIPTION: Projeto usado para validar o contexto browserless.\n"
                "POWERPACK_PROJECT_CONTEXT_OK"
            ),
            project_id="g-p-test123",
            project_name="Projeto Exemplo",
            response_id="resp_test",
        )

    monkeypatch.setattr(module, "run_project_review", fake_review)
    args = SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        effort="high",
        max_conversations=2,
        include_assistant_text=True,
    )
    report = module.run(args)

    assert report["ok"] is True
    assert report["classification"] == "CHATGPT_PROJECT_IDENTITY_SMOKE_PASSED"
    assert report["evidence"]["project_name_exact_match"] is True
    assert report["evidence"]["description_max_100_words"] is True
    assert report["request"]["project_binding_configured"] is True
    assert report["request"]["project_context_serialized"] is True
    assert report["timing"]["steps"]


def test_run_fails_when_model_returns_wrong_project_name(monkeypatch, tmp_path: Path) -> None:
    module = _load()
    _write_binding(tmp_path)

    monkeypatch.setattr(
        module,
        "run_project_review",
        lambda **kwargs: SimpleNamespace(
            text=(
                "PROJECT_NAME: Outro Projeto\n"
                "PROJECT_DESCRIPTION: Descrição válida, mas projeto incorreto.\n"
                "POWERPACK_PROJECT_CONTEXT_OK"
            ),
            project_id="g-p-test123",
            project_name="Projeto Exemplo",
            response_id="resp_test",
        ),
    )
    args = SimpleNamespace(
        path=str(tmp_path),
        model="gpt-5.6-sol",
        effort="high",
        max_conversations=2,
        include_assistant_text=False,
    )
    report = module.run(args)
    assert report["ok"] is False
    assert report["evidence"]["project_name_exact_match"] is False
