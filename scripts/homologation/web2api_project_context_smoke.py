#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.request
from typing import Any


DEFAULT_PROMPT = (
    "me diga qual é o nome do projeto e sua principal missão, produza uma resposta simplificada "
    "de no máximo 100 palavras. e me responda quanto é 1 +1"
)


def _request_json(method: str, url: str, *, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json; charset=utf-8"} if data is not None else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Web2API HTTP {exc.code}: {detail[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not reach local Web2API: {exc}") from exc
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Web2API returned non-JSON output") from exc


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _project_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        value = payload.get("data")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _assistant_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    return str(message.get("content") or "").strip()


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.project_id.startswith("g-p-"):
        raise ValueError("--project-id must be a ChatGPT Project id (g-p-...)")

    endpoint = f"http://127.0.0.1:{args.port}"
    health = _request_json("GET", endpoint + "/health", timeout=10)
    projects_payload = _request_json("GET", endpoint + "/v1/projects", timeout=30)
    projects = _project_items(projects_payload)
    project = next(
        (
            item
            for item in projects
            if str(item.get("id") or item.get("project_id") or item.get("gizmo_id") or "") == args.project_id
        ),
        None,
    )
    if project is None:
        return {
            "ok": False,
            "stage": "web2api-project-context-smoke",
            "classification": "WEB2API_PROJECT_NOT_VISIBLE",
            "evidence": {
                "health_reachable": True,
                "projects_endpoint_reachable": True,
                "project_visible": False,
            },
            "raw_secrets_included": False,
        }

    project_name = str(project.get("name") or project.get("title") or project.get("display_name") or args.project_id).strip()
    payload = {
        "model": args.model or "auto",
        "stream": False,
        "project_id": args.project_id,
        "messages": [{"role": "user", "content": args.prompt}],
    }
    response_payload = _request_json(
        "POST",
        endpoint + "/v1/chat/completions",
        payload=payload,
        timeout=max(30, int(args.response_timeout)),
    )
    response = _assistant_text(response_payload)
    words = len(response.split()) if response else 0
    arithmetic = bool(
        re.search(r"(^|\D)2(\D|$)", response)
        or re.search(r"\bdois\b", response, re.IGNORECASE)
        or re.search(r"\btwo\b", response, re.IGNORECASE)
    )
    project_name_seen = bool(
        project_name
        and project_name != args.project_id
        and _normalized(project_name) in _normalized(response)
    )
    max_words = bool(response) and words <= 100
    accepted = bool(response and arithmetic and project_name_seen and max_words)

    report: dict[str, Any] = {
        "ok": accepted,
        "stage": "web2api-project-context-smoke",
        "classification": (
            "WEB2API_PROJECT_CONTEXT_SMOKE_PASSED"
            if accepted
            else "WEB2API_PROJECT_CONTEXT_CONTRACT_FAILED"
        ),
        "request": {
            "transport": "chatgpt-web2api-rest",
            "project_id": args.project_id,
            "model": args.model or "auto",
            "prompt_is_historical_smoke": args.prompt == DEFAULT_PROMPT,
            "github_plugin_requested": False,
            "direct_chatgpt_backend_submit_used": False,
        },
        "evidence": {
            "health_reachable": bool(health),
            "projects_endpoint_reachable": True,
            "project_visible": True,
            "project_name": project_name,
            "assistant_response_complete": bool(response),
            "project_name_seen": project_name_seen,
            "arithmetic_check": arithmetic,
            "max_words_check": max_words,
            "response_words": words,
            "conversation_id_present": bool(
                isinstance(response_payload, dict)
                and (response_payload.get("conversation_id") or response_payload.get("id"))
            ),
        },
        "raw_secrets_included": False,
    }
    if args.include_assistant_text:
        report["assistant_text"] = response
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the historical ChatGPT Project smoke through the local "
            "ChatGPT-Web2API REST surface: ask for Project name/mission and 1+1."
        )
    )
    parser.add_argument("--port", type=int, default=8097)
    parser.add_argument("--cdp-port", type=int, default=9231)  # lifecycle compatibility; intentionally unused here
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--model", default="auto")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--mention-timeout", type=float, default=0.0)  # lifecycle compatibility; no GitHub gate
    parser.add_argument("--response-timeout", type=float, default=240.0)
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()

    try:
        report = run(args)
    except Exception as exc:
        report = {
            "ok": False,
            "stage": "web2api-project-context-smoke",
            "classification": "WEB2API_PROJECT_CONTEXT_BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
            "raw_secrets_included": False,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
