#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from speckit_powerpack.backend_compat import install_backend_compat
from speckit_powerpack.chatgpt_project_provider import (
    ChatGPTBackendClient,
    ChatGPTProjectError,
    run_project_review,
)
from speckit_powerpack.github_connector_discovery import (
    GitHubConnectorDiscoveryError,
    discover_github_connector,
)
from speckit_powerpack.project_context_smoke import PROJECT_CONTEXT_SMOKE_PROMPT


install_backend_compat()

EXPECTED_PROVIDER = "chatgpt-project"
EXPECTED_MODE = "backend-api"
EXPECTED_AUTHORIZATION = "codex-backend-api"


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
    project_url = str(web.get("project_url") or "").strip()

    if provider != EXPECTED_PROVIDER:
        raise RuntimeError(
            f"Repository is not bound to ChatGPTProjectProvider: provider={provider or '<missing>'}. "
            "Run 'speckit-powerpack review setup --path <repo>' and choose a ChatGPT Project."
        )
    if mode != EXPECTED_MODE:
        raise RuntimeError(
            f"Repository binding is not the recovered browserless backend mode: mode={mode or '<missing>'}."
        )
    if authorization != EXPECTED_AUTHORIZATION:
        raise RuntimeError(
            "Repository binding is not authorized through the recovered Codex/backend-api flow: "
            f"authorization={authorization or '<missing>'}."
        )
    if not project_id.startswith("g-p-"):
        raise RuntimeError("Repository binding does not contain a valid ChatGPT Project id (g-p-...).")
    if not project_name:
        raise RuntimeError("Repository binding does not contain the expected ChatGPT Project name.")

    return {
        "provider": provider,
        "mode": mode,
        "authorization": authorization,
        "project_id": project_id,
        "project_name": project_name,
        "project_url": project_url,
    }


def _evaluate(response: str, expected_project_name: str) -> dict[str, Any]:
    text = response.strip()
    word_count = len(re.findall(r"\S+", text))
    arithmetic_ok = bool(
        re.search(r"(?<!\d)2(?!\d)", text)
        or re.search(r"\bdois\b", text, flags=re.IGNORECASE)
        or re.search(r"\btwo\b", text, flags=re.IGNORECASE)
    )
    project_name_ok = bool(
        expected_project_name
        and expected_project_name.casefold() in text.casefold()
    )
    length_ok = 0 < word_count <= 100
    return {
        "response_non_empty": bool(text),
        "project_name_present": project_name_ok,
        "one_plus_one_equals_two": arithmetic_ok,
        "max_100_words": length_ok,
        "word_count": word_count,
        "mission_semantics": "MANUAL_VERIFY_IN_RESPONSE",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_path = Path(args.path).resolve()
    binding = _load_binding(project_path)

    github_report: dict[str, Any] | None = None
    if args.discover_github:
        github_state = discover_github_connector(
            ChatGPTBackendClient(),
            locale=args.locale,
        )
        github_report = github_state.safe_report()

    result = run_project_review(
        prompt=PROJECT_CONTEXT_SMOKE_PROMPT,
        project_id_or_url=binding["project_id"],
        model=args.model,
        effort=args.effort,
        max_conversations=min(max(0, args.max_conversations), 2),
    )
    response = result.text.strip()
    checks = _evaluate(response, binding["project_name"])
    binding_matches_result = bool(
        result.project_id == binding["project_id"]
        and result.project_name
        and result.project_name.casefold() == binding["project_name"].casefold()
    )
    accepted = bool(
        all(
            checks[key]
            for key in (
                "response_non_empty",
                "project_name_present",
                "one_plus_one_equals_two",
                "max_100_words",
            )
        )
        and binding_matches_result
        and (not args.discover_github or bool(github_report and github_report.get("ok")))
    )

    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "chatgpt-project-backend-smoke",
        "classification": (
            "CHATGPT_PROJECT_BACKEND_SMOKE_PASSED"
            if accepted
            else "CHATGPT_PROJECT_BACKEND_SMOKE_CONTRACT_FAILED"
        ),
        "request": {
            "transport": "chatgpt-backend-api",
            "auth_source": "~/.codex/auth.json",
            "project_bound_before_prompt": True,
            "project_id": binding["project_id"],
            "project_name": binding["project_name"],
            "model": args.model,
            "effort": args.effort,
            "max_conversations": min(max(0, args.max_conversations), 2),
            "prompt": PROJECT_CONTEXT_SMOKE_PROMPT,
            "browser_used": False,
            "cdp_used": False,
            "web2api_used": False,
            "github_plugin_discovery_requested": bool(args.discover_github),
            "github_plugin_requested_in_prompt": False,
        },
        "evidence": {
            "binding_provider": binding["provider"],
            "binding_mode": binding["mode"],
            "binding_authorization": binding["authorization"],
            "binding_matches_review_result": binding_matches_result,
            "response_id_present": bool(result.response_id),
            "github_discovery": github_report,
            **checks,
        },
        "raw_secrets_included": False,
    }
    if args.include_assistant_text:
        report["assistant_text"] = response
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the recovered browserless ChatGPT Project smoke: require an existing "
            "repository->Project binding, optionally discover/validate the GitHub plugin and connector "
            "through read-only ChatGPT backend APIs, build Project context through backend reads, "
            "then send the historical name/mission + 1+1 prompt through /backend-api/codex/responses."
        )
    )
    parser.add_argument("--path", default=".")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--max-conversations", type=int, default=2)
    parser.add_argument("--discover-github", action="store_true")
    parser.add_argument("--locale", default="pt-BR")
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
            "stage": "chatgpt-project-backend-smoke",
            "classification": "CHATGPT_PROJECT_BACKEND_SMOKE_BLOCKED",
            "error": str(exc),
            "request": {
                "transport": "chatgpt-backend-api",
                "browser_used": False,
                "cdp_used": False,
                "web2api_used": False,
                "github_plugin_discovery_requested": bool(args.discover_github),
                "github_plugin_requested_in_prompt": False,
            },
            "raw_secrets_included": False,
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
