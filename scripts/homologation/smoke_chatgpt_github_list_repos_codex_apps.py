#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Iterator

from speckit_powerpack.backend_compat import install_backend_compat
from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError
from speckit_powerpack.codex_apps_smoke_runtime import (
    CODEX_APPS_SERVER,
    parse_codex_jsonl as _parse_codex_jsonl,
    run_codex_exec as _run_codex_exec,
)
from speckit_powerpack.github_connector_discovery import (
    GitHubConnectorDiscoveryError,
    discover_github_connector,
)


install_backend_compat()

MARKER = "POWERPACK_GITHUB_LIST_REPOS_OK"
BASE_PROMPT = "liste todos os meus repositorios"
REPO_LINE_RE = re.compile(r"^\s*REPO\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
TOTAL_RE = re.compile(r"^\s*TOTAL\s+(\d+)\s*$", re.MULTILINE)


class _StepTimer:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()
        self.steps: list[dict[str, Any]] = []

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        print(f"[timing] start {name}", file=sys.stderr, flush=True)
        status = "ok"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - started
            entry = {
                "name": name,
                "elapsed_seconds": round(elapsed, 3),
                "status": status,
            }
            self.steps.append(entry)
            print(
                f"[timing] done  {name}: {elapsed:.3f}s status={status}",
                file=sys.stderr,
                flush=True,
            )

    def report(self) -> dict[str, Any]:
        total = time.perf_counter() - self.started_at
        measured = sum(float(step["elapsed_seconds"]) for step in self.steps)
        return {
            "total_seconds": round(total, 3),
            "measured_steps_seconds": round(measured, 3),
            "steps": list(self.steps),
        }


def _build_prompt(*, connector_id: str) -> str:
    return f"""{BASE_PROMPT}

Use exclusivamente o conector GitHub instalado nesta conta, selecionado explicitamente por esta menção Codex App:
[$github](app://{connector_id})

Objetivo do smoke:
- Liste TODOS os repositórios que esse conector GitHub consegue acessar para a minha conta.
- Inclua públicos e privados que estejam visíveis ao conector.
- Se a ferramenta for paginada, continue consultando páginas até não existir próxima página.
- Você DEVE realmente usar o GitHub App/tool antes de responder.

Restrições:
- Não execute comandos shell.
- Não leia o checkout local para descobrir repositórios.
- Não use web search.
- Não use outro app/connector.
- Não modifique nenhum estado no GitHub.
- Se o GitHub App/tool estiver indisponível, responda exatamente TOOL_UNAVAILABLE.

Formato obrigatório da resposta final, sem tabela e sem omitir repositórios:
REPO owner/name
REPO owner/name
...
TOTAL N
{MARKER}

N deve ser exatamente a quantidade de linhas REPO únicas retornadas.
"""


def _parse_repo_listing(text: str) -> dict[str, Any]:
    repos = REPO_LINE_RE.findall(text)
    unique_repos = list(dict.fromkeys(repos))
    total_match = TOTAL_RE.search(text)
    declared_total = int(total_match.group(1)) if total_match else None
    return {
        "repos": unique_repos,
        "repo_count": len(unique_repos),
        "duplicate_repo_lines": len(repos) - len(unique_repos),
        "declared_total": declared_total,
        "total_present": declared_total is not None,
        "total_matches_unique_repo_count": declared_total == len(unique_repos) if declared_total is not None else False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    timer = _StepTimer()

    with timer.step("validate_working_directory"):
        project_path = Path(args.path).resolve()
        if not project_path.is_dir():
            raise RuntimeError(f"Smoke working directory does not exist: {project_path}")

    with timer.step("initialize_backend_client"):
        client = ChatGPTBackendClient()

    with timer.step("github_chat_preflight"):
        github_state = discover_github_connector(client, locale=args.locale)

    with timer.step("build_prompt"):
        prompt = _build_prompt(connector_id=github_state.connector_id)

    with timer.step("codex_exec"):
        completed = _run_codex_exec(
            project_path=project_path,
            model=args.model,
            prompt=prompt,
            timeout=args.timeout,
        )

    with timer.step("parse_codex_jsonl"):
        parsed = _parse_codex_jsonl(completed.stdout, connector_id=github_state.connector_id)
        assistant_text = str(parsed["assistant_text"])

    with timer.step("parse_repository_listing"):
        listing = _parse_repo_listing(assistant_text)

    with timer.step("evaluate_contract"):
        explicit_app_mention_bound = f"app://{github_state.connector_id}" in prompt
        github_tool_call_observed = parsed["codex_apps_completed_call_count"] > 0
        github_tool_result_observed = parsed["codex_apps_result_call_count"] > 0
        github_identity_in_event = bool(parsed["github_identity_in_event"])
        no_local_fallback = parsed["command_execution_count"] == 0
        no_web_fallback = parsed["web_search_count"] == 0
        marker_seen = MARKER in assistant_text
        tool_unavailable = assistant_text.strip() == "TOOL_UNAVAILABLE"
        list_contract_ok = bool(
            listing["repo_count"] > 0
            and listing["duplicate_repo_lines"] == 0
            and listing["total_present"]
            and listing["total_matches_unique_repo_count"]
        )

        accepted = bool(
            completed.returncode == 0
            and github_state.ok
            and explicit_app_mention_bound
            and github_tool_call_observed
            and github_tool_result_observed
            and github_identity_in_event
            and no_local_fallback
            and no_web_fallback
            and parsed["turn_completed"]
            and not parsed["turn_failed"]
            and marker_seen
            and list_contract_ok
            and not tool_unavailable
        )

        if accepted:
            classification = "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_SMOKE_PASSED"
        elif not no_local_fallback or not no_web_fallback:
            classification = "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_FALLBACK_DETECTED"
        elif tool_unavailable or not github_tool_call_observed:
            classification = "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_TOOL_UNAVAILABLE"
        elif not list_contract_ok:
            classification = "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_LIST_CONTRACT_FAILED"
        else:
            classification = "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_SMOKE_CONTRACT_FAILED"

    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "chatgpt-github-list-repos-codex-apps-smoke",
        "classification": classification,
        "request": {
            "transport": "codex-cli-runtime",
            "auth_source": "~/.codex/auth.json",
            "browser_used": False,
            "cdp_used": False,
            "web2api_used": False,
            "direct_codex_responses_submit_used": False,
            "project_context_used": False,
            "native_project_binding": False,
            "response_visible_in_project": False,
            "explicit_app_mention": True,
            "prompt_intent": BASE_PROMPT,
            "model": args.model,
            "sandbox": "read-only",
            "ephemeral": True,
        },
        "timing": timer.report(),
        "evidence": {
            "github_chat_preflight": github_state.safe_report(),
            "github_codex_runtime": {
                "explicit_app_mention_bound": explicit_app_mention_bound,
                "codex_apps_server": CODEX_APPS_SERVER,
                "codex_apps_call_count": parsed["codex_apps_call_count"],
                "completed_call_count": parsed["codex_apps_completed_call_count"],
                "tool_result_count": parsed["codex_apps_result_call_count"],
                "tool_names": parsed["codex_apps_tools"],
                "github_identity_in_event": github_identity_in_event,
                "github_tool_call_observed": github_tool_call_observed,
                "github_tool_result_observed": github_tool_result_observed,
            },
            "repository_listing": {
                "repo_count": listing["repo_count"],
                "declared_total": listing["declared_total"],
                "duplicate_repo_lines": listing["duplicate_repo_lines"],
                "total_present": listing["total_present"],
                "total_matches_unique_repo_count": listing["total_matches_unique_repo_count"],
                "format_contract_passed": list_contract_ok,
            },
            "no_local_shell_fallback": no_local_fallback,
            "no_web_search_fallback": no_web_fallback,
            "turn_completed": parsed["turn_completed"],
            "turn_failed": parsed["turn_failed"],
            "marker_seen": marker_seen,
            "tool_unavailable": tool_unavailable,
            "codex_exit_code": completed.returncode,
            "json_event_count": parsed["event_count"],
            "json_parse_errors": parsed["json_parse_errors"],
            "stderr_present": bool(completed.stderr.strip()),
            "completeness_scope": "all repositories reported accessible by the selected GitHub connector; not independently enumerated outside that connector",
        },
        "raw_secrets_included": False,
    }
    if args.include_repositories:
        report["repositories"] = listing["repos"]
    if args.include_assistant_text:
        report["assistant_text"] = assistant_text
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browserless smoke that explicitly selects the installed GitHub Codex App and asks it "
            "to list every repository accessible through that connector. PASS requires structural "
            "codex_apps MCP tool/result evidence, no shell/web fallback and a self-consistent list."
        )
    )
    parser.add_argument("--path", default=".", help="Working directory passed to codex exec; no Project binding is required.")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--locale", default="pt-BR")
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
            "stage": "chatgpt-github-list-repos-codex-apps-smoke",
            "classification": "CHATGPT_GITHUB_LIST_REPOS_CODEX_APPS_SMOKE_BLOCKED",
            "error": str(exc),
            "request": {
                "transport": "codex-cli-runtime",
                "browser_used": False,
                "cdp_used": False,
                "web2api_used": False,
                "direct_codex_responses_submit_used": False,
                "project_context_used": False,
                "explicit_app_mention": True,
            },
            "raw_secrets_included": False,
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
