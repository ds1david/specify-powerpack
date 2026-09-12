#!/usr/bin/env python3
"""Homologate the proven ChatGPT Web Project + GitHub connector transport.

This intentionally exercises the same package transport used by
``speckit.implement-review``: Codex auth, Sentinel requirements, native Project
binding, dynamic GitHub connector selection, SSE parsing and JIT allow.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from speckit_powerpack.backend_compat import install_backend_compat  # noqa: E402
from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient  # noqa: E402
from speckit_powerpack.chatgpt_web_review import ChatGPTWebReviewClient  # noqa: E402
from speckit_powerpack.github_connector_discovery import discover_github_connector  # noqa: E402


def _origin_repo(path: Path) -> str:
    value = subprocess.check_output(
        ["git", "-C", str(path), "config", "--get", "remote.origin.url"],
        text=True,
    ).strip()
    value = value.removesuffix(".git")
    if value.startswith("git@github.com:"):
        return value.removeprefix("git@github.com:")
    marker = "github.com/"
    if marker in value:
        return value.split(marker, 1)[1].lstrip("/")
    raise RuntimeError(f"origin is not a GitHub repository: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="ChatGPT Project id or URL")
    parser.add_argument("--path", type=Path, default=Path("."), help="local checkout")
    parser.add_argument("--repo", help="owner/repo; defaults to origin")
    parser.add_argument("--pr", type=int, default=15)
    parser.add_argument("--model", default="gpt-5-6-thinking")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--locale", default="pt-BR")
    args = parser.parse_args()

    install_backend_compat()
    checkout = args.path.resolve()
    repository = args.repo or _origin_repo(checkout)
    backend = ChatGPTBackendClient()
    usage = backend.validate_auth()
    rate_limit = usage.get("rate_limit") if isinstance(usage, dict) else None
    if isinstance(rate_limit, dict) and rate_limit.get("limit_reached"):
        reset = int((rate_limit.get("primary_window") or {}).get("reset_after_seconds") or 0)
        raise RuntimeError(f"ChatGPT rate limit reached; retry in about {reset}s")

    project = backend.get_project(args.project)
    github = discover_github_connector(backend, locale=args.locale)
    if not github.ok:
        raise RuntimeError("GitHub connector is installed but not ready for a live homologation")

    print(f"[homologation] project={project.id} name={project.name}")
    print(f"[homologation] repo={repository} connector={github.connector_id}")
    web = ChatGPTWebReviewClient()
    prompts = (
        "Name the bound Project and summarize its mission in at most 100 words.",
        "Using the selected GitHub connector, list the repositories available to this account.",
        f"Using the selected GitHub connector, list only the files changed in PR #{args.pr} of {repository}.",
    )
    for index, prompt in enumerate(prompts, 1):
        print(f"\n===== TURN {index} =====")
        reply = web.ask(
            prompt,
            project_id=project.id,
            connector_id=github.connector_id,
            repository=repository,
            model=args.model,
            effort=args.effort,
        )
        if not reply.strip():
            raise RuntimeError(f"turn {index} returned no text")
        print(
            "[homologation] authorization="
            f"{'REQUESTED_AND_ALLOWED' if web.last_allow_sent else 'NOT_REQUESTED'} "
            f"tool_calls={len(web.last_tool_invocations)} "
            f"conversation={web.conversation_id} parent={web.parent_message_id}"
        )
        print(reply)
    print("\n[homologation] CHATGPT_WEB_PROJECT_GITHUB_SSE_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
