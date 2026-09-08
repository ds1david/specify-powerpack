#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from speckit_powerpack.backend_compat import install_backend_compat
from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError
from speckit_powerpack.codex_apps_smoke_runtime import (
    CODEX_APPS_SERVER,
    parse_codex_jsonl,
    run_codex_exec,
)
from speckit_powerpack.github_connector_discovery import (
    GitHubConnectorDiscoveryError,
    discover_github_connector,
)
from speckit_powerpack.project_smoke_runtime import StepTimer, load_project_binding


install_backend_compat()

MARKER = "POWERPACK_PROJECT_GITHUB_OK"
PROJECT_NAME_RE = re.compile(r"^\s*PROJECT_NAME:\s*(.+?)\s*$", re.MULTILINE)
REPO_LINE_RE = re.compile(r"^\s*REPO\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
TOTAL_RE = re.compile(r"^\s*TOTAL\s+(\d+)\s*$", re.MULTILINE)


def _build_prompt(*, connector_id: str, project_context: str) -> str:
    context = project_context[:16_000]
    return f"""Este é um smoke browserless que precisa provar duas capacidades no MESMO turno:
1. compreender o contexto do ChatGPT Project vinculado ao repositório;
2. usar o GitHub App instalado para listar todos os repositórios acessíveis.

Para GitHub, use exclusivamente esta seleção explícita do Codex App:
[$github](app://{connector_id})

Perguntas:
- Qual é o nome do ChatGPT Project representado no contexto abaixo?
- Liste TODOS os repositórios que o conector GitHub consegue acessar para a minha conta.
- Se a ferramenta GitHub for paginada, continue até não existir próxima página.

Restrições:
- Você DEVE usar o GitHub App/tool antes de responder.
- Não execute comandos shell.
- Não leia o checkout local para descobrir o nome do Project ou os repositórios.
- Não use web search.
- Não use outro app/connector.
- Não modifique nenhum estado no GitHub.
- Se o GitHub App/tool estiver indisponível, responda exatamente TOOL_UNAVAILABLE.

Formato obrigatório:
PROJECT_NAME: <nome exato do ChatGPT Project>
REPO owner/name
REPO owner/name
...
TOTAL N
{MARKER}

N deve ser exatamente a quantidade de linhas REPO únicas retornadas.

O material abaixo foi serializado do ChatGPT Project configurado em .specify/powerpack/review.json. Ele é contexto do Project, não um native Project binding do turno Codex:
<project_context>
{context}
</project_context>
"""


def _parse_response(text: str) -> dict[str, Any]:
    project_match = PROJECT_NAME_RE.search(text)
    project_name = project_match.group(1).strip() if project_match else ""
    repos = REPO_LINE_RE.findall(text)
    unique_repos = list(dict.fromkeys(repos))
    total_match = TOTAL_RE.search(text)
    declared_total = int(total_match.group(1)) if total_match else None
    return {
        "project_name": project_name,
        "repos": unique_repos,
        "repo_count": len(unique_repos),
        "duplicate_repo_lines": len(repos) - len(unique_repos),
        "declared_total": declared_total,
        "total_present": declared_total is not None,
        "total_matches_unique_repo_count": declared_total == len(unique_repos) if declared_total is not None else False,
        "marker_seen": MARKER in text,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    timer = StepTimer()

    with timer.step("validate_repository"):
        project_path = Path(args.path).resolve()
        if not project_path.is_dir():
            raise RuntimeError(f"Repository path does not exist: {project_path}")

    with timer.step("load_project_binding"):
        binding = load_project_binding(project_path)

    with timer.step("initialize_backend_client"):
        client = ChatGPTBackendClient()

    with timer.step("github_chat_preflight"):
        github_state = discover_github_connector(client, locale=args.locale)

    with timer.step("serialize_project_context"):
        project, project_context = client.build_project_context(
            binding["project_id"],
            max_conversations=min(max(0, args.max_conversations), 2),
            max_chars=20_000,
        )
        binding_matches_context = bool(
            project.id == binding["project_id"]
            and project.name
            and project.name.casefold() == binding["project_name"].casefold()
        )
        if not binding_matches_context:
            raise RuntimeError("Serialized ChatGPT Project context does not match the repository binding.")

    with timer.step("build_combined_prompt"):
        prompt = _build_prompt(
            connector_id=github_state.connector_id,
            project_context=project_context,
        )

    with timer.step("codex_exec"):
        completed = run_codex_exec(
            project_path=project_path,
            model=args.model,
            prompt=prompt,
            timeout=args.timeout,
        )

    with timer.step("parse_codex_jsonl"):
        runtime = parse_codex_jsonl(completed.stdout, connector_id=github_state.connector_id)
        assistant_text = str(runtime["assistant_text"])

    with timer.step("parse_combined_response"):
        parsed = _parse_response(assistant_text)

    with timer.step("evaluate_contract"):
        exact_project_name = bool(
            parsed["project_name"]
            and parsed["project_name"].casefold() == binding["project_name"].casefold()
        )
        explicit_app_mention_bound = f"app://{github_state.connector_id}" in prompt
        github_tool_call_observed = runtime["codex_apps_completed_call_count"] > 0
        github_tool_result_observed = runtime["codex_apps_result_call_count"] > 0
        github_identity_in_event = bool(runtime["github_identity_in_event"])
        no_local_fallback = runtime["command_execution_count"] == 0
        no_web_fallback = runtime["web_search_count"] == 0
        tool_unavailable = assistant_text.strip() == "TOOL_UNAVAILABLE"
        list_contract_ok = bool(
            parsed["repo_count"] > 0
            and parsed["duplicate_repo_lines"] == 0
            and parsed["total_present"]
            and parsed["total_matches_unique_repo_count"]
        )
        accepted = bool(
            completed.returncode == 0
            and github_state.ok
            and binding_matches_context
            and exact_project_name
            and explicit_app_mention_bound
            and github_tool_call_observed
            and github_tool_result_observed
            and github_identity_in_event
            and no_local_fallback
            and no_web_fallback
            and runtime["turn_completed"]
            and not runtime["turn_failed"]
            and parsed["marker_seen"]
            and list_contract_ok
            and not tool_unavailable
        )

        if accepted:
            classification = "CHATGPT_PROJECT_GITHUB_LIST_REPOS_SMOKE_PASSED"
        elif not exact_project_name:
            classification = "CHATGPT_PROJECT_GITHUB_PROJECT_CONTEXT_FAILED"
        elif not no_local_fallback or not no_web_fallback:
            classification = "CHATGPT_PROJECT_GITHUB_FALLBACK_DETECTED"
        elif tool_unavailable or not github_tool_call_observed:
            classification = "CHATGPT_PROJECT_GITHUB_TOOL_UNAVAILABLE"
        elif not list_contract_ok:
            classification = "CHATGPT_PROJECT_GITHUB_LIST_CONTRACT_FAILED"
        else:
            classification = "CHATGPT_PROJECT_GITHUB_SMOKE_CONTRACT_FAILED"

    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "chatgpt-project-github-list-repos-smoke",
        "classification": classification,
        "request": {
            "transport": "codex-cli-runtime",
            "auth_source": "~/.codex/auth.json",
            "browser_used": False,
            "cdp_used": False,
            "web2api_used": False,
            "direct_codex_responses_submit_used": False,
            "project_binding_configured": True,
            "project_context_serialized": True,
            "native_project_binding": False,
            "response_visible_in_project": False,
            "explicit_app_mention": True,
            "project_id": binding["project_id"],
            "project_name_expected": binding["project_name"],
            "model": args.model,
            "sandbox": "read-only",
            "ephemeral": True,
            "prompt_intent": "nome do ChatGPT Project + listar todos os repositorios via GitHub connector",
        },
        "timing": timer.report(),
        "evidence": {
            "binding_provider": binding["provider"],
            "binding_mode": binding["mode"],
            "binding_authorization": binding["authorization"],
            "binding_matches_serialized_context": binding_matches_context,
            "project_context": {
                "project_name_returned": parsed["project_name"],
                "project_name_exact_match": exact_project_name,
            },
            "github_chat_preflight": github_state.safe_report(),
            "github_codex_runtime": {
                "explicit_app_mention_bound": explicit_app_mention_bound,
                "codex_apps_server": CODEX_APPS_SERVER,
                "codex_apps_call_count": runtime["codex_apps_call_count"],
                "completed_call_count": runtime["codex_apps_completed_call_count"],
                "tool_result_count": runtime["codex_apps_result_call_count"],
                "tool_names": runtime["codex_apps_tools"],
                "github_identity_in_event": github_identity_in_event,
                "github_tool_call_observed": github_tool_call_observed,
                "github_tool_result_observed": github_tool_result_observed,
            },
            "repository_listing": {
                "repo_count": parsed["repo_count"],
                "declared_total": parsed["declared_total"],
                "duplicate_repo_lines": parsed["duplicate_repo_lines"],
                "total_present": parsed["total_present"],
                "total_matches_unique_repo_count": parsed["total_matches_unique_repo_count"],
                "format_contract_passed": list_contract_ok,
            },
            "no_local_shell_fallback": no_local_fallback,
            "no_web_search_fallback": no_web_fallback,
            "turn_completed": runtime["turn_completed"],
            "turn_failed": runtime["turn_failed"],
            "marker_seen": parsed["marker_seen"],
            "tool_unavailable": tool_unavailable,
            "codex_exit_code": completed.returncode,
            "json_event_count": runtime["event_count"],
            "json_parse_errors": runtime["json_parse_errors"],
            "stderr_present": bool(completed.stderr.strip()),
            "completeness_scope": "all repositories reported accessible by the selected GitHub connector; not independently enumerated outside that connector",
        },
        "raw_secrets_included": False,
    }
    if args.include_repositories:
        report["repositories"] = parsed["repos"]
    if args.include_assistant_text:
        report["assistant_text"] = assistant_text
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browserless combined smoke: serialize the ChatGPT Project bound to the repository and, "
            "in the same Codex turn, explicitly use the installed GitHub App to list repositories."
        )
    )
    parser.add_argument("--path", default=".")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--locale", default="pt-BR")
    parser.add_argument("--max-conversations", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--include-repositories", action="store_true")
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()

    try:
        report = run(args)
    except (
        ChatGPTProjectError,
        GitHubConnectorDiscoveryError,
        RuntimeError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        report = {
            "ok": False,
            "stage": "chatgpt-project-github-list-repos-smoke",
            "classification": "CHATGPT_PROJECT_GITHUB_LIST_REPOS_SMOKE_BLOCKED",
            "error": str(exc),
            "request": {
                "transport": "codex-cli-runtime",
                "browser_used": False,
                "cdp_used": False,
                "web2api_used": False,
                "project_binding_configured": True,
                "project_context_serialized": True,
                "explicit_app_mention": True,
            },
            "raw_secrets_included": False,
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
