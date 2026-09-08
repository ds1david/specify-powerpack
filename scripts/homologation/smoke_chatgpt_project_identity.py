#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from speckit_powerpack.backend_compat import install_backend_compat
from speckit_powerpack.chatgpt_project_provider import ChatGPTProjectError, run_project_review
from speckit_powerpack.project_smoke_runtime import StepTimer, load_project_binding


install_backend_compat()

MARKER = "POWERPACK_PROJECT_CONTEXT_OK"
PROMPT = f"""Qual é o nome do ChatGPT Project vinculado a este repositório?
Responda também com uma descrição abreviada do projeto em no máximo 100 palavras.
Use o contexto do ChatGPT Project disponibilizado pelo provider para responder.

Formato obrigatório:
PROJECT_NAME: <nome exato do Project>
PROJECT_DESCRIPTION: <descrição abreviada em uma única linha, com no máximo 100 palavras>
{MARKER}
"""
NAME_RE = re.compile(r"^\s*PROJECT_NAME:\s*(.+?)\s*$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^\s*PROJECT_DESCRIPTION:\s*(.+?)\s*$", re.MULTILINE)


def _parse_response(text: str) -> dict[str, Any]:
    name_match = NAME_RE.search(text)
    description_match = DESCRIPTION_RE.search(text)
    name = name_match.group(1).strip() if name_match else ""
    description = description_match.group(1).strip() if description_match else ""
    description_word_count = len(re.findall(r"\S+", description))
    return {
        "project_name": name,
        "description": description,
        "description_word_count": description_word_count,
        "description_present": bool(description),
        "description_max_100_words": 0 < description_word_count <= 100,
        "marker_seen": MARKER in text,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    timer = StepTimer()

    with timer.step("validate_repository"):
        project_path = Path(args.path).resolve()
        if not project_path.is_dir():
            raise RuntimeError(f"Repository path does not exist: {project_path}")

    with timer.step("load_project_binding"):
        binding = load_project_binding(project_path)

    with timer.step("project_context_and_model_response"):
        result = run_project_review(
            prompt=PROMPT,
            project_id_or_url=binding["project_id"],
            model=args.model,
            effort=args.effort,
            max_conversations=min(max(0, args.max_conversations), 2),
        )
        assistant_text = result.text.strip()

    with timer.step("parse_response"):
        parsed = _parse_response(assistant_text)

    with timer.step("evaluate_contract"):
        binding_matches_result = bool(
            result.project_id == binding["project_id"]
            and result.project_name
            and result.project_name.casefold() == binding["project_name"].casefold()
        )
        exact_project_name = bool(
            parsed["project_name"]
            and parsed["project_name"].casefold() == binding["project_name"].casefold()
        )
        accepted = bool(
            binding_matches_result
            and exact_project_name
            and parsed["description_present"]
            and parsed["description_max_100_words"]
            and parsed["marker_seen"]
            and bool(assistant_text)
        )
        classification = (
            "CHATGPT_PROJECT_IDENTITY_SMOKE_PASSED"
            if accepted
            else "CHATGPT_PROJECT_IDENTITY_SMOKE_CONTRACT_FAILED"
        )

    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "chatgpt-project-identity-smoke",
        "classification": classification,
        "request": {
            "transport": "chatgpt-backend-api",
            "auth_source": "~/.codex/auth.json",
            "browser_used": False,
            "cdp_used": False,
            "web2api_used": False,
            "project_binding_configured": True,
            "project_context_serialized": True,
            "native_project_binding": False,
            "response_visible_in_project": False,
            "project_id": binding["project_id"],
            "project_name_expected": binding["project_name"],
            "model": args.model,
            "effort": args.effort,
            "max_conversations": min(max(0, args.max_conversations), 2),
            "prompt_intent": "nome do projeto e descrição abreviada em no máximo 100 palavras",
        },
        "timing": timer.report(),
        "evidence": {
            "binding_provider": binding["provider"],
            "binding_mode": binding["mode"],
            "binding_authorization": binding["authorization"],
            "binding_matches_review_result": binding_matches_result,
            "response_id_present": bool(result.response_id),
            "project_name_returned": parsed["project_name"],
            "project_name_exact_match": exact_project_name,
            "description_present": parsed["description_present"],
            "description_word_count": parsed["description_word_count"],
            "description_max_100_words": parsed["description_max_100_words"],
            "marker_seen": parsed["marker_seen"],
        },
        "raw_secrets_included": False,
    }
    if args.include_assistant_text:
        report["assistant_text"] = assistant_text
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browserless smoke for the ChatGPT Project bound in .specify/powerpack/review.json. "
            "It asks for the exact Project name and a description of at most 100 words."
        )
    )
    parser.add_argument("--path", default=".")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--max-conversations", type=int, default=2)
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()

    try:
        report = run(args)
    except (ChatGPTProjectError, RuntimeError, OSError, ValueError) as exc:
        report = {
            "ok": False,
            "stage": "chatgpt-project-identity-smoke",
            "classification": "CHATGPT_PROJECT_IDENTITY_SMOKE_BLOCKED",
            "error": str(exc),
            "request": {
                "transport": "chatgpt-backend-api",
                "browser_used": False,
                "cdp_used": False,
                "web2api_used": False,
            },
            "raw_secrets_included": False,
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
