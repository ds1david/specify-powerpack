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
    ephemeral: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run one browserless Codex turn and expose its JSONL lifecycle.

    Codex owns App/MCP resolution, approvals, tool execution and continuation.
    PowerPack deliberately does not reproduce the private Responses tool loop.

    With ``progress`` set, the turn is streamed: stdout is read line by line and
    the callback is invoked per event plus a periodic heartbeat, so a long
    ``xhigh`` review is observable instead of a silent multi-minute hang.

    ``ephemeral`` (default true, DECISIONS_AND_TRADEOFFS.md §8) keeps the turn
    un-persisted. Pass ``ephemeral=False`` to write a local rollout under
    `~/.codex/sessions/` (and let it surface in the Codex web history) — an
    audit-trail experiment, at the state-leakage cost §8 accepts against.
    """
    codex = shutil.which("codex")
    if not codex:
        raise CodexAppsError("Codex CLI was not found on PATH. Install Codex and run 'codex login' first.")
    command = [
        codex,
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "-C",
        str(project_path),
        # Keep the turn hermetic. `--ignore-user-config` drops the operator's
        # `~/.codex/config.toml` — MCP servers, hooks, plugins, features — while
        # still using CODEX_HOME for auth. Without this, e.g. a context-mode
        # indexer hook fires on every tool call and turns a 5-minute review into
        # a 40-minute one. The GitHub App is resolved from the `app://` mention
        # in the prompt, not from MCP config, so it still works.
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--disable",
        "hooks",
        "--disable",
        "plugin_hooks",
        "--disable",
        "memories",
    ]
    if ephemeral:
        command.append("--ephemeral")
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

    try:
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
    finally:
        if proc.poll() is None:
            proc.kill()


def _safe(fn: ProgressFn, payload: dict[str, Any]) -> None:
    try:
        fn(payload)
    except Exception:  # progress reporting must never break the review
        pass


class ProgressReporter:
    """Stateful, low-noise progress for one `run_codex_exec` turn.

    Codex emits an event per tool call *and* per update, so a deep review of a
    large PR produces hundreds of `github.fetch_file` events. Rather than echo
    each one, this keeps running counters and prints a rolled-up status line at
    most every ~15 s (plus one-off milestones: turn start/end, a rejected
    shell/web attempt, the verdict draft)."""

    _SUMMARY_EVERY = 30.0

    def __init__(self, phase: str, stream: Any) -> None:
        self.phase = phase
        self.stream = stream
        self.started_at = time.monotonic()
        self.last_summary = 0.0
        self.turn_started = False
        self.drafting = False
        self.tool_counts: dict[str, int] = {}
        self.tool_total = 0
        self.other_total = 0
        self._seen_done: set[str] = set()

    def _emit(self, message: str) -> None:
        print(f"  [{self.phase}] {message}", file=self.stream, flush=True)

    def _summary(self) -> None:
        self.last_summary = time.monotonic()
        elapsed = time.monotonic() - self.started_at
        if not self.tool_total:
            self._emit(f"working… {elapsed / 60:.1f} min elapsed")
            return
        top = sorted(self.tool_counts.items(), key=lambda kv: -kv[1])[:3]
        detail = ", ".join(f"{name.split('.')[-1]}×{count}" for name, count in top)
        extra = f" +{self.other_total} other" if self.other_total else ""
        self._emit(
            f"working… {self.tool_total} GitHub calls ({detail}){extra} · {elapsed / 60:.1f} min"
        )

    def __call__(self, payload: dict[str, Any]) -> None:
        kind = payload.get("kind")
        if kind == "heartbeat":
            self._summary()
            return
        if kind != "event":
            return
        event = payload.get("event") or {}
        etype = str(event.get("type") or "")
        if etype in {"thread.started", "turn.started"}:
            if not self.turn_started:
                self.turn_started = True
                self._emit("codex turn started — reading the PR through the GitHub App")
            return
        if etype == "turn.completed":
            self._summary()
            self._emit("✓ turn completed")
            return
        if etype in {"turn.failed", "error"}:
            self._emit("✗ turn failed")
            return
        item = event.get("item") if isinstance(event.get("item"), dict) else None
        if not item:
            return
        itype = str(item.get("type") or "")
        if itype == "mcp_tool_call":
            status = str(item.get("status") or "")
            if status in {"completed", "failed"}:
                marker = str(item.get("id") or f"{item.get('tool')}:{self.tool_total + self.other_total}")
                if marker not in self._seen_done:
                    self._seen_done.add(marker)
                    if str(item.get("server") or "") == CODEX_APPS_SERVER:
                        tool = str(item.get("tool") or "tool")
                        self.tool_counts[tool] = self.tool_counts.get(tool, 0) + 1
                        self.tool_total += 1
                    else:
                        self.other_total += 1
            if time.monotonic() - self.last_summary > self._SUMMARY_EVERY:
                self._summary()
            return
        if itype == "command_execution":
            self._emit("⚠ shell command attempted (rejected — GitHub evidence only)")
            return
        if itype == "web_search":
            self._emit("⚠ web search attempted (rejected — GitHub evidence only)")
            return
        if itype == "agent_message" and not self.drafting:
            self.drafting = True
            self._emit("· drafting the review verdict…")


def make_progress_reporter(phase: str, stream: Any) -> ProgressReporter:
    return ProgressReporter(phase, stream)


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
