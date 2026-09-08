from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "homologation" / "web2api_project_context_smoke.py"
ENTRYPOINT = ROOT / "scripts" / "homologation" / "smoke_chatgpt_project_web2api.py"
PS1 = ROOT / "scripts" / "homologation" / "smoke_chatgpt_project_web2api.ps1"
HISTORICAL_PROMPT = (
    "me diga qual é o nome do projeto e sua principal missão, produza uma resposta simplificada "
    "de no máximo 100 palavras. e me responda quanto é 1 +1"
)


def _load_helper():
    spec = importlib.util.spec_from_file_location("web2api_project_context_smoke", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_preserves_historical_project_prompt() -> None:
    helper = _load_helper()
    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

    assert helper.DEFAULT_PROMPT == HISTORICAL_PROMPT
    assert HISTORICAL_PROMPT in entrypoint


def test_smoke_uses_only_local_web2api_rest_surface() -> None:
    text = HELPER.read_text(encoding="utf-8")

    assert 'endpoint + "/v1/projects"' in text
    assert 'endpoint + "/v1/chat/completions"' in text
    assert '"project_id": args.project_id' in text
    assert '"messages": [{"role": "user", "content": args.prompt}]' in text
    assert "ChatGPTBackendClient" not in text
    assert "~/.codex/auth.json" not in text
    assert "chatgpt_web2api.cdp_driver" not in text
    assert "websockets" not in text
    assert "/backend-api/f/conversation" not in text
    assert "@GitHub" not in text


def test_smoke_requires_project_context_arithmetic_and_length_contract() -> None:
    text = HELPER.read_text(encoding="utf-8")

    assert '"project_name_seen": project_name_seen' in text
    assert '"arithmetic_check": arithmetic' in text
    assert '"max_words_check": max_words' in text
    assert '"response_words": words' in text
    assert "WEB2API_PROJECT_CONTEXT_SMOKE_PASSED" in text
    assert "WEB2API_PROJECT_CONTEXT_CONTRACT_FAILED" in text


def test_project_name_normalization_is_accent_and_punctuation_tolerant() -> None:
    helper = _load_helper()

    name = "Estratégia — Evolução!"
    response = "O projeto se chama Estrategia Evolucao e sua missão é testar estratégias. 1 + 1 = 2."
    assert helper._normalized(name) in helper._normalized(response)


def test_windows_lifecycle_reuses_pinned_web2api_and_same_profile_as_github_probe() -> None:
    text = PS1.read_text(encoding="utf-8")

    assert "497527dceabfa3f95961e23c291e618c5570f1ac" in text
    assert "Octo-Lex/ChatGPT-Web2API/archive/$Web2ApiRevision.zip" in text
    assert '[string]$Profile = "web2api-github-probe"' in text
    assert '"-m", "chatgpt_web2api", "start"' in text
    assert '"--port", [string]$Port' in text
    assert '"--project-id", $ProjectId' in text


def test_entrypoint_is_web2api_only_and_requires_explicit_project_id() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")

    assert 'parser.add_argument("--project-id", required=True)' in text
    assert '"web2api_only": True' in text
    assert "ChatGPTBackendClient" not in text
    assert "chatgpt_project_provider" not in text
    assert "~/.codex" not in text
    assert "_resolve_connector" not in text
    assert "probe_chatgpt_github" not in text
