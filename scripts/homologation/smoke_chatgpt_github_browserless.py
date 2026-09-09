#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speckit_powerpack.chatgpt_project_provider import ChatGPTProjectError  # noqa: E402
from speckit_powerpack.github_browserless_smoke import run_github_browserless_smoke  # noqa: E402
from speckit_powerpack.github_connector_preflight import GitHubConnectorError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browserless GitHub smoke: discover the installed GitHub plugin with Codex auth, "
            "then ask /backend-api/codex/responses to list repositories. Pass only if a GitHub "
            "tool call is observed. Does not reconstruct /f/conversation or use a browser."
        )
    )
    parser.add_argument("--locale", default="pt-BR")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()
    try:
        report = run_github_browserless_smoke(
            locale=args.locale,
            model=args.model,
            effort=args.effort,
            include_assistant_text=args.include_assistant_text,
        )
    except (ChatGPTProjectError, GitHubConnectorError, OSError, ValueError) as exc:
        report = {
            "ok": False,
            "stage": "chatgpt-github-browserless-smoke",
            "classification": "GITHUB_CONNECTOR_PREFLIGHT_FAILED",
            "error": str(exc),
            "request": {
                "transport": "chatgpt-backend-api",
                "browser_used": False,
                "cdp_used": False,
                "web2api_used": False,
                "conversation_submit_used": False,
            },
            "raw_secrets_included": False,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
