#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from web2api_github_driver_probe import DEFAULT_PROMPT  # noqa: E402


PS1 = SCRIPT_DIR / "probe_chatgpt_github_web2api.ps1"
HELPER = SCRIPT_DIR / "web2api_github_driver_probe.py"


def _windows_path(path: Path) -> str:
    try:
        proc = subprocess.run(
            ["wslpath", "-w", str(path)],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("wslpath is required to run the Windows Web2API probe from WSL") from exc
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or f"Could not convert path for Windows: {path}")
    return proc.stdout.strip()


def _parse_child_json(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise RuntimeError("Web2API probe produced no JSON output")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        # Keep diagnostics bounded and never echo raw browser/network material.
        raise RuntimeError("Web2API probe returned non-JSON output") from None
    if not isinstance(value, dict):
        raise RuntimeError("Web2API probe returned a non-object JSON value")
    return value


def run_web2api(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    if not shutil.which("powershell.exe"):
        raise RuntimeError("powershell.exe is unavailable; this probe currently targets WSL + Windows Web2API")
    ps1 = _windows_path(PS1)
    helper = _windows_path(HELPER)
    argv = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ps1,
        "-HelperPath",
        helper,
        "-Port",
        str(args.port),
        "-CdpPort",
        str(args.cdp_port),
        "-Profile",
        args.profile,
        "-Model",
        args.model,
        "-Prompt",
        args.prompt,
        "-MentionTimeoutSec",
        str(args.mention_timeout),
        "-ResponseTimeoutSec",
        str(args.response_timeout),
    ]
    if args.project_id:
        argv += ["-ProjectId", args.project_id]
    if args.no_install:
        argv += ["-NoInstall"]
    if args.include_assistant_text:
        argv += ["-IncludeAssistantText"]

    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=max(int(args.response_timeout) + 360, 420),
        check=False,
    )
    child = _parse_child_json(proc.stdout)
    return child, proc.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Web2API-only GitHub capability probe: type an @GitHub prompt through "
            "the pinned ChatGPT-Web2API Chrome/CDP path, require native connector "
            "materialization before Send, and validate the completed response."
        )
    )
    parser.add_argument("--port", type=int, default=8097)
    parser.add_argument("--cdp-port", type=int, default=9231)
    parser.add_argument("--profile", default="web2api-github-probe")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--mention-timeout", type=float, default=25.0)
    parser.add_argument("--response-timeout", type=float, default=240.0)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()

    if not args.prompt.lstrip().casefold().startswith("@github"):
        print(json.dumps({
            "ok": False,
            "stage": "web2api-github-orchestration",
            "classification": "INVALID_PROMPT",
            "error": "Prompt must begin with @GitHub",
            "web2api_executed": False,
            "raw_secrets_included": False,
        }, ensure_ascii=False, indent=2))
        return 2

    try:
        child, stderr = run_web2api(args)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        report = {
            "ok": False,
            "stage": "web2api-github-orchestration",
            "classification": "WEB2API_LIFECYCLE_BLOCKED",
            "error": str(exc),
            "web2api_only": True,
            "raw_secrets_included": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    report = {
        "ok": bool(child.get("ok")),
        "stage": "web2api-github-orchestration",
        "classification": child.get("classification") or "WEB2API_UNKNOWN",
        "web2api_only": True,
        "web2api": child,
        "lifecycle_log_present": bool(stderr),
        "raw_secrets_included": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
