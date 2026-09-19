from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError, CodexTurn
from .github_connector_preflight import GitHubConnectorError, discover_github_connector


GITHUB_BROWSERLESS_SMOKE_PROMPT = (
    "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM "
    "POWERPACK_GITHUB_TOOL_OK"
)
MARKER = "POWERPACK_GITHUB_TOOL_OK"
GITHUB_SMOKE_INSTRUCTIONS = (
    "You are a GitHub-connected assistant. If a GitHub plugin/connector/tool is available "
    "in this session, use it to list the authenticated user's repositories. "
    "Do not invent repository names. If no GitHub tool is available, say BLOCKED_CAPABILITY "
    "and do not fabricate a repository list."
)


def classify_github_browserless_smoke(*, preflight_ok: bool, github_tool_invoked: bool, marker_seen: bool) -> tuple[bool, str]:
    if not preflight_ok:
        return False, "GITHUB_CONNECTOR_PREFLIGHT_FAILED"
    if not github_tool_invoked:
        return False, "GITHUB_TOOL_NOT_MATERIALIZED"
    if not marker_seen:
        return False, "GITHUB_BROWSERLESS_SMOKE_INCOMPLETE"
    return True, "GITHUB_BROWSERLESS_SMOKE_PASSED"


def run_github_browserless_smoke(
    *,
    client: ChatGPTBackendClient | None = None,
    locale: str = "en-US",
    model: str = "gpt-5.6-sol",
    effort: str = "high",
    include_assistant_text: bool = True,
) -> dict[str, Any]:
    backend = client or ChatGPTBackendClient()
    preflight = discover_github_connector(backend, locale=locale)
    turn: CodexTurn | None = None
    if preflight.get("ok"):
        turn = backend.codex_turn(
            prompt=GITHUB_BROWSERLESS_SMOKE_PROMPT,
            instructions=GITHUB_SMOKE_INSTRUCTIONS,
            model=model,
            effort=effort,
        )
    marker_seen = bool(turn and MARKER in turn.text)
    github_tool_invoked = bool(turn and turn.github_tool_invoked)
    accepted, classification = classify_github_browserless_smoke(
        preflight_ok=bool(preflight.get("ok")),
        github_tool_invoked=github_tool_invoked,
        marker_seen=marker_seen,
    )
    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "chatgpt-github-browserless-smoke",
        "classification": classification,
        "request": {
            "transport": "chatgpt-backend-api",
            "auth_source": "~/.codex/auth.json",
            "prompt": GITHUB_BROWSERLESS_SMOKE_PROMPT,
            "model": model,
            "effort": effort,
            "browser_used": False,
            "cdp_used": False,
            "web2api_used": False,
            "conversation_submit_used": False,
            "github_plugin_requested": True,
            "github_mention": "@GitHub",
        },
        "evidence": {
            "github_connector_preflight": bool(preflight.get("ok")),
            "github_plugin_resolved": bool((preflight.get("github_plugin") or {}).get("resolved")),
            "github_oauth_active": (preflight.get("authorization") or {}).get("auth_status") == "ACTIVE",
            "github_tool_invoked": github_tool_invoked,
            "github_tool_count": len(turn.tool_names) if turn else 0,
            "marker_seen": marker_seen,
            "response_id_present": bool(turn and turn.response_id),
            "codex_auth_is_not_web_composer": True,
        },
        "preflight": preflight,
        "raw_secrets_included": False,
    }
    if include_assistant_text and turn is not None:
        report["assistant_text"] = turn.text
    if classification == "GITHUB_TOOL_NOT_MATERIALIZED":
        report["error"] = (
            "GitHub plugin/connector is installed and OAuth-active, but /backend-api/codex/responses "
            "did not materialize a GitHub tool call. @GitHub in the prompt is only a capability hint "
            "on this browserless transport."
        )
    return report


def install_github_browserless_smoke(provider_cli) -> None:
    original_smoke = provider_cli.cmd_review_smoke
    powerpack_error = provider_cli.core.PowerPackError

    def cmd_review_smoke(args) -> None:
        if getattr(args, "flow", None) != "github":
            original_smoke(args)
            return
        project = Path(args.path).resolve()
        try:
            flow_report = run_github_browserless_smoke(
                locale="pt-BR",
                model=args.model,
                effort=args.effort,
                include_assistant_text=True,
            )
        except (ChatGPTProjectError, GitHubConnectorError) as exc:
            flow_report = {
                "ok": False,
                "stage": "chatgpt-github-browserless-smoke",
                "classification": "GITHUB_CONNECTOR_PREFLIGHT_FAILED",
                "error": str(exc),
                "raw_secrets_included": False,
            }
        report = {"ok": bool(flow_report.get("ok")), "flows": {"github": flow_report}}
        if flow_report.get("assistant_text"):
            print("\n=== CHATGPT GITHUB BROWSERLESS SMOKE RESPONSE ===")
            print(flow_report["assistant_text"])
            print("=== END CHATGPT GITHUB BROWSERLESS SMOKE RESPONSE ===\n")
        smoke_dir = project / ".specify" / "powerpack" / "smoke"
        smoke_dir.mkdir(parents=True, exist_ok=True)
        report_path = smoke_dir / "github-browserless.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["ok"]:
            raise powerpack_error(f"GitHub browserless smoke failed. See {report_path}")

    provider_cli.cmd_review_smoke = cmd_review_smoke
