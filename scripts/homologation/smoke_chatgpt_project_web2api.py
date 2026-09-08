#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PS1 = SCRIPT_DIR / "smoke_chatgpt_project_web2api.ps1"
HELPER = SCRIPT_DIR / "web2api_project_context_smoke.py"
DEFAULT_PROMPT = (
    "me diga qual é o nome do projeto e sua principal missão, produza uma resposta simplificada "
    "de no máximo 100 palavras. e me responda quanto é 1 +1"
)


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
        raise RuntimeError("wslpath is required to run the Windows Web2API smoke from WSL") from exc
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or f"Could not convert path for Windows: {path}")
    return proc.stdout.strip()


def _parse_json(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise RuntimeError("Web2API project smoke produced no JSON output")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("Web2API project smoke returned non-JSON output") from None
    if not isinstance(value, dict):
        raise RuntimeError("Web2API project smoke returned a non-object JSON value")
    return value


def run(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    if not shutil.which("powershell.exe"):
        raise RuntimeError("powershell.exe is unavailable; this smoke currently targets WSL + Windows Web2API")
    argv = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        _windows_path(PS1),
        "-HelperPath",
        _windows_path(HELPER),
        "-ProjectId",
        args.project_id,
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
        "-ResponseTimeoutSec",
        str(args.response_timeout),
    ]
    if args.no_install:
        argv.append("-NoInstall")
    if args.include_assistant_text:
        argv.append("-IncludeAssistantText")

    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=max(int(args.response_timeout) + 360, 420),
        check=False,
    )
    return _parse_json(proc.stdout), proc.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the historical functional ChatGPT Project smoke through "
            "ChatGPT-Web2API only, without GitHub plugin or Codex/browserless preflight."
        )
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--port", type=int, default=8097)
    parser.add_argument("--cdp-port", type=int, default=9231)
    parser.add_argument("--profile", default="web2api-github-probe")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--response-timeout", type=float, default=240.0)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()

    if not args.project_id.startswith("g-p-"):
        print(json.dumps({
            "ok": False,
            "stage": "web2api-project-context-orchestration",
            "classification": "INVALID_PROJECT_ID",
            "error": "--project-id must begin with g-p-",
            "web2api_only": True,
            "raw_secrets_included": False,
        }, ensure_ascii=False, indent=2))
        return 2

    try:
        child, stderr = run(args)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        report = {
            "ok": False,
            "stage": "web2api-project-context-orchestration",
            "classification": "WEB2API_PROJECT_SMOKE_LIFECYCLE_BLOCKED",
            "error": str(exc),
            "web2api_only": True,
            "raw_secrets_included": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    report = {
        "ok": bool(child.get("ok")),
        "stage": "web2api-project-context-orchestration",
        "classification": child.get("classification") or "WEB2API_PROJECT_SMOKE_UNKNOWN",
        "web2api_only": True,
        "historical_prompt_recovered": args.prompt == DEFAULT_PROMPT,
        "web2api": child,
        "lifecycle_log_present": bool(stderr),
        "raw_secrets_included": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
