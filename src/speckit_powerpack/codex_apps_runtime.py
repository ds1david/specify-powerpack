from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


CODEX_APPS_SERVER = "codex_apps"


class CodexAppsError(RuntimeError):
    pass


def run_codex_exec(
    *,
    project_path: Path,
    model: str,
    prompt: str,
    timeout: int,
    effort: str = "xhigh",
) -> subprocess.CompletedProcess[str]:
    """Run one browserless Codex turn and expose its JSONL lifecycle.

    Codex owns App/MCP resolution, approvals, tool execution and continuation.
    PowerPack deliberately does not reproduce the private Responses tool loop.
    """
    codex = shutil.which("codex")
    if not codex:
        raise CodexAppsError("Codex CLI was not found on PATH. Install Codex and run 'codex login' first.")
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
    if effort.strip():
        command.extend(["-c", f'model_reasoning_effort="{effort.strip()}"'])
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
        raise CodexAppsError(f"codex exec timed out after {timeout}s") from exc
    except OSError as exc:
        raise CodexAppsError(f"Could not execute Codex CLI: {exc}") from exc


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
        if value == connector_id or "github" in value.casefold():
            return True
    return False


def parse_codex_jsonl(raw: str, *, connector_id: str) -> dict[str, Any]:
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
                call = {
                    "server": server,
                    "tool": str(thread_item.get("tool") or ""),
                    "status": str(thread_item.get("status") or ""),
                    "result_present": thread_item.get("result") is not None,
                    "error_present": thread_item.get("error") is not None,
                    "github_identity": _event_mentions_github(thread_item, connector_id),
                }
                codex_apps_calls.append(call)
                github_identity_in_event = github_identity_in_event or bool(call["github_identity"])

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
        "calls": codex_apps_calls,
    }


def require_github_tool_evidence(parsed: dict[str, Any]) -> None:
    if parsed.get("command_execution_count"):
        raise CodexAppsError("Review used a local shell fallback; GitHub evidence must come through Codex Apps.")
    if parsed.get("web_search_count"):
        raise CodexAppsError("Review used web-search fallback; GitHub evidence must come through Codex Apps.")
    if not parsed.get("turn_completed") or parsed.get("turn_failed"):
        raise CodexAppsError("Codex turn did not complete successfully.")
    if int(parsed.get("codex_apps_completed_call_count") or 0) < 1:
        raise CodexAppsError("No completed codex_apps MCP tool call was observed.")
    if int(parsed.get("codex_apps_result_call_count") or 0) < 1:
        raise CodexAppsError("No successful codex_apps MCP tool result was observed.")
    if not parsed.get("github_identity_in_event"):
        raise CodexAppsError("The Codex Apps lifecycle could not be attributed to GitHub.")
