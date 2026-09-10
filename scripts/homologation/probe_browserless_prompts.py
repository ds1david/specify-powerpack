#!/usr/bin/env python3
"""Browserless prompt probe.

Submits three prompts through the **ChatGPT backend Codex Responses API**
(`POST https://chatgpt.com/backend-api/codex/responses`) — the transport that
surfaces in the ChatGPT web / Codex history — bound to a ChatGPT Project by
serializing its context into the request `instructions`. Same auth
(`~/.codex/auth.json`), same Project, same GitHub connector the browserless
review uses; no separate flow.

    python3 scripts/homologation/probe_browserless_prompts.py \
        --project g-p-6a9ba1a060208191a5b6e03a3950b183 --effort medium --keep-session

The three prompts:
  1. name + mission of this project (<=100 words)   [uses the Project context]
  2. list all my GitHub repositories                 [uses the GitHub connector]
  3. list only the files changed in PR #15           [uses the GitHub connector]

WARNING: this spends Codex/ChatGPT tokens on your plan.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from speckit_powerpack.chatgpt_project_provider import (  # noqa: E402
    ChatGPTBackendClient,
    ChatGPTProjectError,
)

try:  # connector discovery is best-effort — the probe still runs without it
    from speckit_powerpack.github_connector_discovery import (  # noqa: E402
        GitHubConnectorDiscoveryError,
        discover_github_connector,
    )
except ImportError:  # pragma: no cover
    discover_github_connector = None
    GitHubConnectorDiscoveryError = Exception  # type: ignore[assignment,misc]

RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


def _origin_repo(path: Path) -> str:
    import subprocess

    try:
        url = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "ds1david/specify-powerpack"
    url = url.removesuffix(".git")
    if url.startswith("git@github.com:"):
        return url.split(":", 1)[1]
    parts = url.split("github.com/", 1)
    return parts[1] if len(parts) == 2 else "ds1david/specify-powerpack"


def _log(kind: str, msg: str) -> None:
    # kind: "browserless" = a chatgpt.com/backend-api call;
    #       "codex"       = a tool/command executed inside the Codex turn.
    print(f"  [{kind}] {msg}", file=sys.stderr, flush=True)


def _stream_response(client: ChatGPTBackendClient, *, prompt: str, instructions: str,
                     model: str, effort: str, store: bool) -> tuple[str, str | None, list[str]]:
    body: dict[str, object] = {
        "model": model,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "instructions": instructions,
        "stream": True,
        "store": store,
    }
    if effort:
        body["reasoning"] = {"effort": effort}
    headers = client._headers(accept="text/event-stream")
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        RESPONSES_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers
    )
    _log("browserless", f"POST {RESPONSES_URL} (model={model} effort={effort} store={store})")
    text: list[str] = []
    response_id: str | None = None
    tool_events: list[str] = []
    seen_tools: set[str] = set()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                etype = str(event.get("type") or "")
                if etype == "response.output_text.delta" and isinstance(event.get("delta"), str):
                    text.append(event["delta"])
                elif etype == "response.completed" and isinstance(event.get("response"), dict):
                    response_id = str(event["response"].get("id") or "") or None
                    _log("browserless", f"response.completed id={response_id or 'n/a'}")
                elif etype == "response.failed":
                    err = (event.get("response") or {}).get("error") or {}
                    raise ChatGPTProjectError(
                        f"response.failed: {err.get('code') or 'unknown'}: {err.get('message') or event}"
                    )
                elif "tool" in etype or "mcp" in etype or "function_call" in etype:
                    tool_events.append(etype)
                    if etype not in seen_tools:
                        seen_tools.add(etype)
                        _log("codex", f"tool event: {etype}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ChatGPTProjectError(f"HTTP {exc.code} from {RESPONSES_URL}: {detail[:1200]}") from exc
    except urllib.error.URLError as exc:
        raise ChatGPTProjectError(f"cannot reach {RESPONSES_URL}: {exc}") from exc
    return "".join(text).strip(), response_id, tool_events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="ChatGPT Project id (g-p-…) or URL")
    parser.add_argument("--pr", default="15", help="PR number for prompt 3 (default 15)")
    parser.add_argument("--path", default=".", help="repo checkout (origin → owner/repo for prompt 3)")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="medium", help="minimal|low|medium|high|xhigh (default medium)")
    parser.add_argument("--keep-session", action="store_true",
                        help='send "store": true so the turn persists in the Codex web history')
    parser.add_argument("--separate", action="store_true",
                        help="submit the 3 prompts as 3 separate turns (3 web items) instead of one")
    parser.add_argument("--locale", default="pt-BR")
    args = parser.parse_args()

    repo = _origin_repo(Path(args.path).resolve())
    print(f"# probe: project={args.project} repo={repo} pr=#{args.pr} "
          f"model={args.model} effort={args.effort} store={bool(args.keep_session)}", file=sys.stderr)
    print("# this spends Codex/ChatGPT tokens on your plan.", file=sys.stderr)

    client = ChatGPTBackendClient()
    _log("browserless", "authenticating with the ChatGPT backend (/backend-api/me)…")
    client.validate_auth()
    _log("browserless", f"reading ChatGPT Project context (/backend-api/gizmos/{args.project} …)…")
    project, context = client.build_project_context(args.project, max_conversations=2)
    _log("browserless", f"bound to Project '{project.name}' ({project.id})")

    github_hint = "Use the installed GitHub connector (mention @GitHub) for anything about GitHub."
    if discover_github_connector is not None:
        try:
            _log("browserless", "discovering the GitHub connector (/backend-api/aip/connectors …)…")
            disc = discover_github_connector(client, locale=args.locale)
            if getattr(disc, "ok", False) and getattr(disc, "connector_id", ""):
                github_hint = (
                    "Use exclusively the installed GitHub App for anything about GitHub:\n"
                    f"[$github](app://{disc.connector_id})"
                )
                _log("browserless", f"GitHub connector: {disc.connector_id}")
        except (ChatGPTProjectError, GitHubConnectorDiscoveryError) as exc:  # type: ignore[misc]
            _log("browserless", f"GitHub connector discovery failed (continuing): {exc}")

    instructions = (
        "You are answering a short connectivity probe for Specify PowerPack. "
        "Treat the ChatGPT Project context below as background memory. "
        "Do not run shell commands. Do not use web search. Do not mutate anything.\n\n"
        f"{github_hint}\n\n"
        "CHATGPT PROJECT CONTEXT (read-only):\n"
        f"<project_context>\n{context[:24000]}\n</project_context>"
    )

    questions = [
        "1) Qual é o nome deste projeto e descreva a missão do projeto em no máximo 100 palavras?",
        "2) Liste todos os meus repositórios no GitHub.",
        f"3) Liste apenas os arquivos que foram modificados no pull request #{args.pr} do repositório {repo}. "
        "Siga a paginação até a lista ficar completa.",
    ]

    turns = questions if args.separate else ["\n\n".join(questions)]
    report: dict[str, object] = {
        "transport": "chatgpt-backend-api /codex/responses",
        "project": {"id": project.id, "name": project.name},
        "repo": repo,
        "store": bool(args.keep_session),
        "turns": [],
    }
    exit_code = 0
    for i, prompt in enumerate(turns, start=1):
        try:
            text, rid, tools = _stream_response(
                client, prompt=prompt, instructions=instructions,
                model=args.model, effort=args.effort, store=bool(args.keep_session),
            )
        except ChatGPTProjectError as exc:
            print(f"\n=== TURN {i}: ERROR ===\n{exc}", file=sys.stderr)
            report["turns"].append({"turn": i, "ok": False, "error": str(exc)})
            exit_code = 1
            break
        print(f"\n=== TURN {i} — response_id={rid or 'n/a'} tools={sorted(set(tools)) or 'none'} ===")
        print(text)
        report["turns"].append({"turn": i, "ok": True, "response_id": rid,
                                "tool_events": sorted(set(tools)), "chars": len(text)})

    out = ROOT / "specs" / "001-single-skill-baseline" / "T025-evidence" / "probe-browserless-prompts.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n# report: {out.relative_to(ROOT)}", file=sys.stderr)
    print("# check the Codex history at https://chatgpt.com/codex "
          f"(and the Project at {project.url})", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
