from speckit_powerpack.project_context_smoke import PROJECT_CONTEXT_SMOKE_PROMPT


def test_project_context_smoke_prompt_is_context_probe_not_code_review() -> None:
    assert PROJECT_CONTEXT_SMOKE_PROMPT == (
        "me diga qual é o nome do projeto e sua principal missão, produza uma resposta "
        "simplificada de no máximo 100 palavras. e me responda quanto é 1 +1"
    )
    assert "code review" not in PROJECT_CONTEXT_SMOKE_PROMPT.casefold()
    assert "ratio(" not in PROJECT_CONTEXT_SMOKE_PROMPT
