#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from speckit_powerpack.backend_compat import install_backend_compat
from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError
from speckit_powerpack.github_connector_discovery import (
    GitHubConnectorDiscoveryError,
    discover_github_connector,
)


install_backend_compat()

EXPECTED_PROVIDER = "chatgpt-project"
EXPECTED_MODE = "backend-api"
EXPECTED_AUTHORIZATION = "codex-backend-api"
CODEX_APPS_SERVER = "codex_apps"
MARKER = "POWERPACK_GITHUB_CONNECTOR_OK"


def _load_binding(project_path: Path) -> dict[str, str]:
    review_path = project_path / ".specify" / "powerpack" / "review.json"
    if not review_path.is_file():
        raise RuntimeError(
            f"PowerPack review binding is missing: {review_path}. "
            "Run 'speckit-powerpack review setup --path <repo>' first."
        )
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read review binding {review_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("PowerPack review config must contain an object.")

    provider = str(payload.get("provider") or "").strip()
    web = payload.get("chatgpt_web") if isinstance(payload.get("chatgpt_web"), dict) else {}
    mode = str(web.get("mode") or "").strip()
    authorization = str(web.get("authorization") or "").strip()
    project_id = str(web.get("project_id") or "").strip()
    project_name = str(web.get("project_name") or "").strip()

    if provider != EXPECTED_PROVIDER:
        raise RuntimeError(
            f"Repository is not configured for ChatGPTProjectProvider: provider={provider or '<missing>'}."
        )
    if mode != EXPECTED_MODE:
        raise RuntimeError(
            f"Repository binding is not browserless backend-api mode: mode={mode or '<missing>'}."
        )
    if authorization != EXPECTED_AUTHORIZATION:
        raise RuntimeError(
            "Repository binding is not authorized through codex-backend-api: "
            f"authorization={authorization or '<missing>'}."
        )
    if not project_id.startswith("g-p-"):
        raise RuntimeError("Repository binding does not contain a valid ChatGPT Project id (g-p-...).")
    if not project_name:
        raise RuntimeError("Repository binding does not contain a ChatGPT Project name.")

    return {
        "provider": provider,
        "mode": mode,
        "authorization": authorization,
        "project_id": project_id,
        "project_name": project_name,
    }


def _github_repo_from_origin(project_path: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_path), "config", "--get", "remote.origin.url"],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Could not inspect git origin: {exc}") from exc
    origin = completed.stdout.strip()
    if completed.returncode != 0 or not origin:
        raise RuntimeError("Could not determine remote.origin.url; pass --github-repo owner/name.")

    patterns = (
        r"^git@github\.com:(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$",
        r"^https?://github\.com/(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?/?$",
    )
    for pattern in patterns:
        match = re.match(pattern, origin, flags=re.IGNORECASE)
        if match:
            return match.group("repo")
    raise RuntimeError(
        "remote.origin.url is not a supported github.com repository URL; pass --github-repo owner/name."
    )


def _build_prompt(*, connector_id: str, repo_full_name: str, project_context: str) -> str:
    context = project_context[:12_000]
    return f"""This is a read-only browserless smoke test.

Use exclusively the installed GitHub app selected by this explicit Codex App mention:
[$github](app://{connector_id})

Through that GitHub app, access repository {repo_full_name} and confirm that the repository is readable. You may read repository metadata or another minimal read-only fact needed to prove access.

Rules:
- You MUST actually use the GitHub app/tool before answering.
- Do NOT run shell commands.
- Do NOT read the local checkout to answer the GitHub portion.
- Do NOT use web search.
- Do NOT use any other app/connector.
- Do NOT modify GitHub state.
- If the GitHub app/tool is unavailable, answer exactly TOOL_UNAVAILABLE.
- On successful GitHub tool use, finish the final answer with: {MARKER} {repo_full_name}

The following ChatGPT Project material is serialized background context only. It is NOT a native Project binding for this Codex turn:
<project_context>
{context}
</project_context>
"""


def _run_codex_exec(
    *,
    project_path: Path,
    model: str,
    prompt: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI was not found on PATH. Install/login to Codex before running this smoke.")
    command = [
        codex,
        "exec",
        "--json",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "-C",
        str(project_path),
    ]
    if model.strip():
        command.extend(["-m", model.strip()])
    command.append(prompt)
    try:
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=max(30, timeout),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"codex exec timed out after {timeout}s") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not execute Codex CLI: {exc}") from exc


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _event_mentions_github(event: dict[str, Any], connector_id: str) -> bool:
    for value in _walk(event):
        if not isinstance(value, str):
            continue
        folded = value.casefold()
        if value == connector_id or "github" in folded:
            return True
    return False


def _parse_codex_jsonl(raw: str, *, connector_id: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    parse_errors = 0
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            item = json.loads(text)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if isinstance(item, dict):
            events.append(item)

    agent_messages: list[str] = []
    codex_apps_calls: list[dict[str, Any]] = []
    command_execution_count = 0
    web_search_count = 0
    turn_completed = False
    turn_failed = False
    github_identity_in_event = False

    for event in events:
        event_type = str(event.get("type") or "")
        if event_type == "turn.completed":
            turn_completed = True
        elif event_type in {"turn.failed", "error"}:
            turn_failed = True

        thread_item = event.get("item") if isinstance(event.get("item"), dict) else None
        if not thread_item:
            continue
        item_type = str(thread_item.get("type") or "")
        if item_type == "agent_message" and isinstance(thread_item.get("text"), str):
            agent_messages.append(thread_item["text"])
        elif item_type == "command_execution":
            command_execution_count += 1
        elif item_type == "web_search":
            web_search_count += 1
        elif item_type == "mcp_tool_call":
            server = str(thread_item.get("server") or "")
            if server == CODEX_APPS_SERVER:
                status = str(thread_item.get("status") or "")
                call = {
                    "server": server,
                    "tool": str(thread_item.get("tool") or ""),
                    "status": status,
                    "result_present": thread_item.get("result") is not None,
                    "error_present": thread_item.get("error") is not None,
                }
                codex_apps_calls.append(call)
                github_identity_in_event = github_identity_in_event or _event_mentions_github(
                    thread_item, connector_id
                )

    assistant_text = "\n".join(part.strip() for part in agent_messages if part.strip()).strip()
    completed_calls = [
        call
        for call in codex_apps_calls
        if call["status"] == "completed" and not call["error_present"]
    ]
    result_calls = [call for call in completed_calls if call["result_present"]]
    return {
        "event_count": len(events),
        "json_parse_errors": parse_errors,
        "turn_completed": turn_completed,
        "turn_failed": turn_failed,
        "assistant_text": assistant_text,
        "codex_apps_call_count": len(codex_apps_calls),
        "codex_apps_completed_call_count": len(completed_calls),
        "codex_apps_result_call_count": len(result_calls),
        "codex_apps_tools": list(dict.fromkeys(call["tool"] for call in codex_apps_calls if call["tool"])),
        "github_identity_in_event": github_identity_in_event,
        "command_execution_count": command_execution_count,
        "web_search_count": web_search_count,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_path = Path(args.path).resolve()
    binding = _load_binding(project_path)
    repo_full_name = args.github_repo.strip() if args.github_repo else _github_repo_from_origin(project_path)
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repo_full_name):
        raise RuntimeError("--github-repo must be in owner/name form.")

    client = ChatGPTBackendClient()
    github_state = discover_github_connector(client, locale=args.locale)
    project, project_context = client.build_project_context(
        binding["project_id"],
        max_conversations=min(max(0, args.max_conversations), 2),
        max_chars=16_000,
    )
    binding_matches_context = bool(
        project.id == binding["project_id"]
        and project.name
        and project.name.casefold() == binding["project_name"].casefold()
    )
    if not binding_matches_context:
        raise RuntimeError("Serialized Project context does not match the repository binding.")

    prompt = _build_prompt(
        connector_id=github_state.connector_id,
        repo_full_name=repo_full_name,
        project_context=project_context,
    )
    completed = _run_codex_exec(
        project_path=project_path,
        model=args.model,
        prompt=prompt,
        timeout=args.timeout,
    )
    parsed = _parse_codex_jsonl(completed.stdout, connector_id=github_state.connector_id)
    assistant_text = str(parsed["assistant_text"])

    explicit_app_mention_bound = f"app://{github_state.connector_id}" in prompt
    github_tool_call_observed = parsed["codex_apps_completed_call_count"] > 0
    github_tool_result_observed = parsed["codex_apps_result_call_count"] > 0
    no_local_fallback = parsed["command_execution_count"] == 0
    no_web_fallback = parsed["web_search_count"] == 0
    marker_seen = MARKER in assistant_text
    repo_seen = repo_full_name.casefold() in assistant_text.casefold()
    tool_unavailable = assistant_text.strip() == "TOOL_UNAVAILABLE"

    accepted = bool(
        completed.returncode == 0
        and github_state.ok
        and binding_matches_context
        and explicit_app_mention_bound
        and github_tool_call_observed
        and github_tool_result_observed
        and no_local_fallback
        and no_web_fallback
        and parsed["turn_completed"]
        and not parsed["turn_failed"]
        and marker_seen
        and repo_seen
        and not tool_unavailable
    )

    if accepted:
        classification = "CHATGPT_GITHUB_CODEX_APPS_SMOKE_PASSED"
    elif not no_local_fallback or not no_web_fallback:
        classification = "CHATGPT_GITHUB_CODEX_APPS_FALLBACK_DETECTED"
    elif tool_unavailable or not github_tool_call_observed:
        classification = "CHATGPT_GITHUB_CODEX_APPS_TOOL_UNAVAILABLE"
    else:
        classification = "CHATGPT_GITHUB_CODEX_APPS_SMOKE_CONTRACT_FAILED"

    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "chatgpt-github-codex-apps-smoke",
        "classification": classification,
        "request": {
            "transport": "codex-cli-runtime",
            "auth_source": "~/.codex/auth.json",
            "browser_used": False,
            "cdp_used": False,
            "web2api_used": False,
            "direct_codex_responses_submit_used": False,
            "project_context_serialized": True,
            "native_project_binding": False,
            "response_visible_in_project": False,
            "explicit_app_mention": True,
            "github_repo": repo_full_name,
            "model": args.model,
            "sandbox": "read-only",
            "ephemeral": True,
        },
        "evidence": {
            "binding_provider": binding["provider"],
            "binding_mode": binding["mode"],
            "binding_authorization": binding["authorization"],
            "binding_matches_serialized_context": binding_matches_context,
            "github_chat_preflight": github_state.safe_report(),
            "github_codex_runtime": {
                "explicit_app_mention_bound": explicit_app_mention_bound,
                "codex_apps_server": CODEX_APPS_SERVER,
                "codex_apps_call_count": parsed["codex_apps_call_count"],
                "completed_call_count": parsed["codex_apps_completed_call_count"],
                "tool_result_count": parsed["codex_apps_result_call_count"],
                "tool_names": parsed["codex_apps_tools"],
                "github_identity_in_event": parsed["github_identity_in_event"],
                "github_tool_call_observed": github_tool_call_observed,
                "github_tool_result_observed": github_tool_result_observed,
                "attribution": (
                    "explicit app:// GitHub mention + successful codex_apps MCP call + requested GitHub repo"
                    if github_tool_call_observed
                    else "not proven"
                ),
            },
            "no_local_shell_fallback": no_local_fallback,
            "no_web_search_fallback": no_web_fallback,
            "turn_completed": parsed["turn_completed"],
            "turn_failed": parsed["turn_failed"],
            "marker_seen": marker_seen,
            "repo_seen_in_final": repo_seen,
            "tool_unavailable": tool_unavailable,
            "codex_exit_code": completed.returncode,
            "json_event_count": parsed["event_count"],
            "json_parse_errors": parsed["json_parse_errors"],
            "stderr_present": bool(completed.stderr.strip()),
        },
        "raw_secrets_included": False,
    }
    if args.include_assistant_text:
        report["assistant_text"] = assistant_text
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browserless GitHub connector smoke. Resolve the installed GitHub connector with the "
            "ChatGPT account preflight, serialize the bound ChatGPT Project context, then delegate "
            "app:// binding, Codex Apps MCP tool exposure/execution and continuation to 'codex exec'."
        )
    )
    parser.add_argument("--path", default=".")
    parser.add_argument("--github-repo", default="")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--max-conversations", type=int, default=2)
    parser.add_argument("--locale", default="pt-BR")
    parser.add_argument("--timeout", type=int, default=300)
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
    ) as exc:
        report = {
            "ok": False,
            "stage": "chatgpt-github-codex-apps-smoke",
            "classification": "CHATGPT_GITHUB_CODEX_APPS_SMOKE_BLOCKED",
            "error": str(exc),
            "request": {
                "transport": "codex-cli-runtime",
                "browser_used": False,
                "cdp_used": False,
                "web2api_used": False,
                "direct_codex_responses_submit_used": False,
                "native_project_binding": False,
            },
            "raw_secrets_included": False,
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
