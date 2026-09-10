from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import threading
import time
from typing import Any, Callable


CODEX_APPS_SERVER = "codex_apps"

# Progress callback: receives {"kind": "event", "event": <parsed dict>} for each
# JSONL line, {"kind": "line", "raw": <str>} for a non-JSON line, and
# {"kind": "heartbeat", "elapsed": <float>} when the turn is quiet for a while.
ProgressFn = Callable[[dict[str, Any]], None]


class CodexAppsError(RuntimeError):
    pass


def run_codex_exec(
    *,
    project_path: Path,
    model: str,
    prompt: str,
    timeout: int,
    effort: str = "xhigh",
    progress: ProgressFn | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one browserless Codex turn and expose its JSONL lifecycle.

    Codex owns App/MCP resolution, approvals, tool execution and continuation.
    PowerPack deliberately does not reproduce the private Responses tool loop.

    With ``progress`` set, the turn is streamed: stdout is read line by line and
    the callback is invoked per event plus a periodic heartbeat, so a long
    ``xhigh`` review is observable instead of a silent multi-minute hang.
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

    deadline = max(30, timeout)
    if progress is None:
        try:
            return subprocess.run(
                command, text=True, capture_output=True, check=False, timeout=deadline
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexAppsError(f"codex exec timed out after {timeout}s") from exc
        except OSError as exc:
            raise CodexAppsError(f"Could not execute Codex CLI: {exc}") from exc

    try:
        proc = subprocess.Popen(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1
        )
    except OSError as exc:
        raise CodexAppsError(f"Could not execute Codex CLI: {exc}") from exc

    out_lines: list[str] = []
    last_activity = [time.monotonic()]

    def _pump() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            out_lines.append(line)
            last_activity[0] = time.monotonic()
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                _safe(progress, {"kind": "line", "raw": stripped})
                continue
            if isinstance(event, dict):
                _safe(progress, {"kind": "event", "event": event})

    reader = threading.Thread(target=_pump, daemon=True)
    reader.start()

    started = time.monotonic()
    while True:
        try:
            proc.wait(timeout=10)
            break
        except subprocess.TimeoutExpired:
            now = time.monotonic()
            if now - started > deadline:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                raise CodexAppsError(f"codex exec timed out after {timeout}s")
            if now - last_activity[0] > 25:
                last_activity[0] = now
                _safe(progress, {"kind": "heartbeat", "elapsed": now - started})

    reader.join(timeout=5)
    stderr = ""
    try:
        stderr = proc.stderr.read() if proc.stderr else ""
    except (OSError, ValueError):
        pass
    return subprocess.CompletedProcess(command, proc.returncode or 0, "".join(out_lines), stderr)


def _safe(fn: ProgressFn, payload: dict[str, Any]) -> None:
    try:
        fn(payload)
    except Exception:  # progress reporting must never break the review
        pass


def format_progress(payload: dict[str, Any], *, phase: str) -> str | None:
    """Turn a `run_codex_exec` progress payload into one compact human line
    (or None to stay silent). `phase` labels which turn ('snapshot' / 'review')."""
    kind = payload.get("kind")
    if kind == "heartbeat":
        return f"  [{phase}] still working… {payload.get('elapsed', 0):.0f}s elapsed"
    if kind == "line":
        raw = str(payload.get("raw") or "")
        return f"  [{phase}] {raw[:160]}" if raw else None
    if kind != "event":
        return None
    event = payload.get("event") or {}
    etype = str(event.get("type") or "")
    if etype in {"thread.started", "turn.started"}:
        return f"  [{phase}] codex turn started"
    if etype == "turn.completed":
        return f"  [{phase}] ✓ turn completed"
    if etype in {"turn.failed", "error"}:
        return f"  [{phase}] ✗ turn failed"
    item = event.get("item") if isinstance(event.get("item"), dict) else None
    if not item:
        return None
    itype = str(item.get("type") or "")
    if itype == "mcp_tool_call":
        server = str(item.get("server") or "")
        tool = str(item.get("tool") or "")
        status = str(item.get("status") or "")
        call = ".".join(part for part in (server, tool) if part) or "tool call"
        return f"  [{phase}] · {call}" + (f" [{status}]" if status else "")
    if itype == "command_execution":
        cmd = str(item.get("command") or "").replace("\n", " ")
        return f"  [{phase}] · ⚠ shell: {cmd[:80]} (will be rejected)"
    if itype == "web_search":
        return f"  [{phase}] · ⚠ web search (will be rejected)"
    if itype == "agent_message":
        text = str(item.get("text") or "")
        return f"  [{phase}] · drafted response ({len(text)} chars)" if text else None
    if itype == "reasoning":
        return f"  [{phase}] · reasoning…"
    return None


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
