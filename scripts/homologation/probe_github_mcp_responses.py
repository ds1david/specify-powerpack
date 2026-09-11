#!/usr/bin/env python3
"""Probe: GitHub remote MCP as a tool on the real OpenAI Responses API.

A sibling of ``probe_browserless_prompts.py`` — but it deliberately does NOT
touch chatgpt.com. It isolates ONE question: *does a remote-MCP `tools` entry
actually get discovered and called by a model?* by using the documented path:

    POST https://api.openai.com/v1/responses
      Authorization: Bearer <OPENAI_API_KEY>        (the platform API key)
      tools: [{ type: "mcp",
                server_url: "https://api.githubcopilot.com/mcp/",
                headers: { Authorization: "Bearer <GITHUB_PAT>",   # NOT the
                           X-MCP-Readonly: "true",                 # tool's
                           X-MCP-Toolsets: "pull_requests" } }]    # `authorization`
      tool_choice: "required"

``OPENAI_API_KEY`` is read from the environment, else from ``~/.codex/auth.json``
(``codex login`` stores one in API-key mode). ``GITHUB_PAT`` (or ``GITHUB_TOKEN``)
from the environment.

Stages (``--stage``):
  * ``discover`` (default) — "what is the title of PR #<pr>?"  (cheapest; proves
    the model can list + call the MCP tools at all)
  * ``files``            — "list every changed file in PR #<pr> with path /
    status / additions / deletions"
  * ``both``             — discover then files

The full response ``status`` / ``error`` / ``output`` (including ``mcp_list_tools``
and ``mcp_call`` items) is printed and saved to
``specs/001-single-skill-baseline/T025-evidence/probe-github-mcp-responses.json``.

WARNING: this spends OpenAI **platform** credit (billed to the API key), not a
ChatGPT plan.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from speckit_powerpack.request_log import log_request

RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MCP_URL = "https://api.githubcopilot.com/mcp/"
EVIDENCE = ROOT / "specs" / "001-single-skill-baseline" / "T025-evidence"


def _log(msg: str) -> None:
    print(f"  [mcp-probe] {msg}", file=sys.stderr, flush=True)


def _openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        data = json.loads((Path.home() / ".codex" / "auth.json").read_text("utf-8"))
        return str(data.get("OPENAI_API_KEY") or "").strip()
    except (OSError, json.JSONDecodeError):
        return ""


def _origin_repo(path: Path) -> str:
    import subprocess
    try:
        url = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "ds1david/specify-powerpack"
    url = url.removesuffix(".git")
    if url.startswith("git@github.com:"):
        return url.split(":", 1)[1]
    parts = url.split("github.com/", 1)
    return parts[1] if len(parts) == 2 else "ds1david/specify-powerpack"


def _mcp_tool(args: argparse.Namespace, pat: str) -> dict[str, object]:
    headers: dict[str, str] = {"Authorization": f"Bearer {pat}"}
    if not args.allow_writes:
        headers["X-MCP-Readonly"] = "true"
    if args.toolsets:
        headers["X-MCP-Toolsets"] = args.toolsets
    tool: dict[str, object] = {
        "type": "mcp",
        "server_label": "github",
        "server_description": "Official GitHub MCP Server",
        "server_url": args.mcp_server_url,
        "headers": headers,
        "require_approval": "never",
    }
    if args.allowed_tools:
        tool["allowed_tools"] = [t.strip() for t in args.allowed_tools.split(",") if t.strip()]
    return tool


def _post(body: dict[str, object], key: str, timeout: int) -> dict[str, object]:
    raw = json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    log_request("POST", RESPONSES_URL, raw, headers)
    req = urllib.request.Request(RESPONSES_URL, data=raw, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            return {"_http_status": exc.code, **json.loads(detail)}
        except json.JSONDecodeError:
            return {"_http_status": exc.code, "error": {"message": detail[:2000]}}
    except urllib.error.URLError as exc:
        return {"error": {"message": f"cannot reach {RESPONSES_URL}: {exc}"}}


def _summarize(resp: dict[str, object]) -> dict[str, object]:
    """Pull the parts that matter: status, error, and each output item's shape."""
    items = []
    for it in (resp.get("output") or []):
        if not isinstance(it, dict):
            continue
        row = {"type": it.get("type")}
        for k in ("name", "server_label", "status", "error"):
            if it.get(k) is not None:
                row[k] = it[k]
        if it.get("type") == "mcp_list_tools":
            tools = it.get("tools") or []
            row["tool_names"] = [t.get("name") for t in tools if isinstance(t, dict)][:60]
        if it.get("type") == "mcp_call":
            out = it.get("output")
            row["output_preview"] = (out if isinstance(out, str) else json.dumps(out))[:1500]
        if it.get("type") == "message":
            row["text"] = "".join(
                c.get("text", "") for c in (it.get("content") or []) if isinstance(c, dict)
            )[:4000]
        items.append(row)
    return {
        "http_status": resp.get("_http_status", 200),
        "status": resp.get("status"),
        "error": resp.get("error"),
        "incomplete_details": resp.get("incomplete_details"),
        "output_items": items,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pr", default="15", help="PR number (default 15)")
    p.add_argument("--path", default=".", help="repo checkout (origin -> owner/repo)")
    p.add_argument("--repo", default="", help="override owner/repo (else from git origin)")
    p.add_argument("--model", default="gpt-5.6", help="OpenAI model (default gpt-5.6)")
    p.add_argument("--effort", default="high", help="reasoning effort (default high)")
    p.add_argument("--stage", choices=("discover", "files", "both"), default="discover")
    p.add_argument("--mcp-server-url", default=DEFAULT_MCP_URL)
    p.add_argument("--toolsets", default="pull_requests",
                   help="X-MCP-Toolsets header (comma list; '' to omit). Default pull_requests")
    p.add_argument("--allowed-tools", default="",
                   help="Responses `allowed_tools` filter (comma list). e.g. pull_request_read")
    p.add_argument("--allow-writes", action="store_true",
                   help="drop the X-MCP-Readonly header (default: read-only)")
    p.add_argument("--tool-choice", default="required",
                   help="Responses tool_choice (default 'required')")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--curl-full", action="store_true",
                   help="write a replayable curl (all headers + keys) to the trace file")
    args = p.parse_args()

    key = _openai_key()
    if not key:
        _log("no OPENAI_API_KEY (env or ~/.codex/auth.json). This probe needs a platform "
             "API key — `codex login` in API-key mode, or export OPENAI_API_KEY.")
        return 2
    pat = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN") or ""
    if not pat:
        _log("no $GITHUB_PAT (or $GITHUB_TOKEN)."); return 2

    repo = args.repo or _origin_repo(Path(args.path).resolve())
    http_log = os.environ.get("SPECKIT_POWERPACK_HTTP_LOG") or str(EVIDENCE / "probe-http-requests.log")
    os.environ["SPECKIT_POWERPACK_HTTP_LOG"] = http_log
    Path(http_log).parent.mkdir(parents=True, exist_ok=True)
    Path(http_log).write_text("", encoding="utf-8")
    if args.curl_full:
        os.environ["SPECKIT_POWERPACK_HTTP_LOG_RAW"] = "1"

    tool = _mcp_tool(args, pat)
    _log(f"endpoint: {RESPONSES_URL}  model={args.model} effort={args.effort} "
         f"tool_choice={args.tool_choice}")
    _log(f"github MCP: {args.mcp_server_url}  "
         f"readonly={not args.allow_writes} toolsets={args.toolsets or '-'} "
         f"allowed_tools={args.allowed_tools or '-'}")
    _log("this spends OpenAI PLATFORM credit (the API key), not a ChatGPT plan.")

    stages = {
        "discover": (f"Consulte o GitHub e diga qual e o titulo do pull request #{args.pr} "
                     f"do repositorio {repo}. Use obrigatoriamente as ferramentas do GitHub MCP."),
        "files": (f"Use obrigatoriamente o GitHub MCP. Liste TODOS os arquivos alterados no "
                  f"pull request #{args.pr} do repositorio {repo}. Para cada arquivo informe "
                  f"path, status, additions e deletions. Siga a paginacao ate a lista ficar completa."),
    }
    todo = ["discover", "files"] if args.stage == "both" else [args.stage]

    report: dict[str, object] = {
        "endpoint": RESPONSES_URL,
        "model": args.model,
        "github_mcp": {
            "server_url": args.mcp_server_url,
            "readonly": not args.allow_writes,
            "toolsets": args.toolsets or None,
            "allowed_tools": tool.get("allowed_tools"),
            "tool_choice": args.tool_choice,
        },
        "repo": repo,
        "stages": [],
    }
    exit_code = 0
    for name in todo:
        prompt = stages[name]
        body: dict[str, object] = {
            "model": args.model,
            "input": prompt,
            "tools": [tool],
            "tool_choice": args.tool_choice,
        }
        if args.effort:
            body["reasoning"] = {"effort": args.effort}
        _log(f"--- stage '{name}': POST …")
        resp = _post(body, key, args.timeout)
        summary = _summarize(resp)
        print(f"\n=== STAGE {name} ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        report["stages"].append({"stage": name, "prompt": prompt, **summary})
        called = [i for i in summary["output_items"] if i.get("type") in ("mcp_call", "mcp_list_tools")]
        if summary["error"] or summary.get("http_status", 200) >= 400:
            exit_code = 1
            break
        _log(f"stage '{name}': {len(called)} MCP item(s); "
             f"status={summary['status']}")

    out = EVIDENCE / "probe-github-mcp-responses.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_curl = sum(1 for ln in Path(http_log).read_text("utf-8").splitlines() if ln.startswith("curl "))
    _log(f"report: {out}")
    _log(f"curl trace: {http_log}  ({n_curl} request(s))")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
