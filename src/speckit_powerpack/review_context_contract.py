from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass
import io
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse


GITHUB_PLUGIN_MENTION = "@GitHub"


@dataclass(frozen=True)
class LocalReviewContext:
    branch: str
    spec_dir: Path


@dataclass(frozen=True)
class WebReviewContext:
    pull_request_number: int
    pull_request_url: str
    repository: str


class ReviewContextError(RuntimeError):
    pass


def _git(project: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=project,
        text=True,
        capture_output=True,
        shell=False,
    )
    if proc.returncode != 0:
        raise ReviewContextError((proc.stderr or proc.stdout or "git command failed").strip())
    return proc.stdout.strip()


def current_branch(project: Path) -> str:
    branch = _git(project, "branch", "--show-current")
    if not branch:
        raise ReviewContextError("Local review requires a named Git branch; detached HEAD is not supported.")
    return branch


def _candidate_spec_names(branch: str) -> list[str]:
    candidates: list[str] = []
    for value in (
        branch,
        branch.removeprefix("spec/"),
        branch.rsplit("/", 1)[-1],
        os.environ.get("SPECIFY_FEATURE", "").strip(),
    ):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def resolve_local_review_context(project: Path) -> LocalReviewContext:
    project = project.resolve()
    branch = current_branch(project)
    specs_root = project / "specs"
    if not specs_root.is_dir():
        raise ReviewContextError(
            f"Local review requires the Spec Kit specs directory: {specs_root}"
        )

    matches: list[Path] = []
    for name in _candidate_spec_names(branch):
        candidate = specs_root / name
        if (candidate / "spec.md").is_file() and candidate not in matches:
            matches.append(candidate)

    if not matches:
        available = sorted(
            path.name for path in specs_root.iterdir()
            if path.is_dir() and (path / "spec.md").is_file()
        )
        suffix_matches = [
            specs_root / name
            for name in available
            if branch.endswith(name) or name.endswith(branch.rsplit("/", 1)[-1])
        ]
        for candidate in suffix_matches:
            if candidate not in matches:
                matches.append(candidate)

    if len(matches) != 1:
        detail = ", ".join(path.name for path in matches) or "none"
        raise ReviewContextError(
            "Could not resolve exactly one Spec Kit SPEC for the current branch "
            f"'{branch}'. Matches: {detail}. Local code review must fail closed instead of reviewing the repository generically."
        )

    return LocalReviewContext(branch=branch, spec_dir=matches[0])


def github_repository(project: Path) -> str:
    remote = _git(project, "remote", "get-url", "origin")
    ssh = re.fullmatch(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?", remote)
    if ssh:
        return f"{ssh.group(1)}/{ssh.group(2)}"

    parsed = urlparse(remote)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        raise ReviewContextError(
            "Web PR review currently requires origin to point to github.com so the ChatGPT/GitHub plugin can target the exact pull request."
        )
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise ReviewContextError(f"Cannot derive owner/repository from origin: {remote}")
    return f"{parts[0]}/{parts[1]}"


def resolve_web_review_context(project: Path, pull_request: str | None) -> WebReviewContext:
    if not pull_request or not str(pull_request).strip():
        raise ReviewContextError(
            "Web code review requires an explicit --pr <number|github-pull-request-url>."
        )

    repository = github_repository(project)
    raw = str(pull_request).strip()
    if raw.isdigit():
        number = int(raw)
        if number < 1:
            raise ReviewContextError("Pull request number must be greater than zero.")
        return WebReviewContext(
            pull_request_number=number,
            pull_request_url=f"https://github.com/{repository}/pull/{number}",
            repository=repository,
        )

    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ReviewContextError("--pr must be a GitHub pull request number or https://github.com/.../pull/<number> URL.")
    match = re.fullmatch(r"/([^/]+)/([^/]+)/pull/(\d+)/?", parsed.path)
    if not match:
        raise ReviewContextError("--pr URL must have the form https://github.com/<owner>/<repo>/pull/<number>.")
    url_repository = f"{match.group(1)}/{match.group(2)}"
    if url_repository.casefold() != repository.casefold():
        raise ReviewContextError(
            f"Pull request repository '{url_repository}' does not match current origin '{repository}'."
        )
    number = int(match.group(3))
    return WebReviewContext(
        pull_request_number=number,
        pull_request_url=f"https://github.com/{repository}/pull/{number}",
        repository=repository,
    )


def local_context_prompt(project: Path) -> str:
    context = resolve_local_review_context(project)
    relative_spec = context.spec_dir.relative_to(project).as_posix()
    return f"""POWERPACK REVIEW CONTEXT — LOCAL MODE (authoritative)
review_mode: local-spec-branch
branch: {context.branch}
spec: {relative_spec}
pull_request: NOT_REQUIRED

Review the implementation for the current Spec Kit SPEC and the current Git branch only.
Use the local repository as evidence, including the SPEC artifacts and the branch implementation.
Do not claim that a GitHub pull request, ChatGPT Project memory, or Web/GitHub plugin context was inspected.
If the branch cannot be tied to this SPEC, stop with BLOCKED_REVIEW_CONTEXT rather than reviewing the repository generically."""


def web_context_prompt(
    project: Path,
    pull_request: str | None,
    *,
    github_plugin_authorized: bool,
) -> str:
    if not github_plugin_authorized:
        raise ReviewContextError(
            "Web code review requires the GitHub app/plugin to be installed and connected in ChatGPT Web or Desktop, with this repository authorized. Configure that first, then rerun with --github-plugin-authorized."
        )
    context = resolve_web_review_context(project, pull_request)
    return f"""{GITHUB_PLUGIN_MENTION}
POWERPACK REVIEW CONTEXT — WEB PR MODE (authoritative)
review_mode: web-pull-request
repository: {context.repository}
pull_request_number: {context.pull_request_number}
pull_request_url: {context.pull_request_url}
github_plugin_authorization: USER_CONFIRMED
github_plugin_invocation: {GITHUB_PLUGIN_MENTION}

The GitHub app/plugin must already be installed and connected in ChatGPT Web or Desktop for the authenticated account, with access to this repository. The leading {GITHUB_PLUGIN_MENTION} mention is intentional and required by the currently homologated Web flow to activate GitHub repository access.

Use the GitHub plugin/connector to open and inspect exactly this pull request.
The pull request parameter is authoritative: do not substitute another PR and do not perform a generic repository review.
Inspect the PR base/head identity, changed files and relevant SPEC evidence before producing a verdict.
If this session exposes no GitHub plugin/connector/tool after the {GITHUB_PLUGIN_MENTION} invocation, stop with BLOCKED_CAPABILITY and state that the current Web transport did not provide the required GitHub capability.
If a GitHub plugin/connector/tool is available but cannot access this exact repository or pull request, stop with BLOCKED_CONFIGURATION and state that GitHub app installation, connection or repository authorization must be granted or repaired in ChatGPT Web/Desktop and GitHub.
Do not infer approval from Project memory, PR description, prior reviews, or green CI alone."""


def _without_leading_github_mention(prompt: str) -> str:
    """Remove one user-supplied leading GitHub mention before canonical composition."""
    return re.sub(
        r"(?is)^\s*@github\b[ \t]*(?:\r?\n)?",
        "",
        prompt or "",
        count=1,
    ).lstrip()


def _blocked_review_status(text: str) -> str | None:
    match = re.search(
        r"(?im)^\s*#*\s*(BLOCKED_(?:CAPABILITY|CONFIGURATION|REVIEW_CONTEXT))\b",
        text or "",
    )
    return match.group(1).upper() if match else None


def install_review_context_contract(provider_cli) -> None:
    """Install provider-specific code-review context rules without changing transport.

    Web/ChatGPT Project reviews require an explicit PR, an installed/connected
    GitHub app/plugin with repository access, a user-confirmed permission grant,
    and an explicit @GitHub invocation. Local Codex reviews derive their context
    from the current Git branch and its current Spec Kit SPEC.
    """

    original_prepare_parser = provider_cli._prepare_parser
    original_cmd_review_run = provider_cli.cmd_review_run

    def cmd_review_run(args: argparse.Namespace) -> None:
        project = Path(args.path).resolve()
        provider = provider_cli._provider_for(project, args.provider)
        try:
            if provider == provider_cli.PROVIDER_CODEX:
                if getattr(args, "pr", None):
                    raise ReviewContextError(
                        "--pr is only valid for Web code review. Local review derives context from the current SPEC and branch."
                    )
                if getattr(args, "github_plugin_authorized", False):
                    raise ReviewContextError(
                        "--github-plugin-authorized is only valid for Web code review."
                    )
                context_prompt = local_context_prompt(project)
            else:
                context_prompt = web_context_prompt(
                    project,
                    getattr(args, "pr", None),
                    github_plugin_authorized=bool(getattr(args, "github_plugin_authorized", False)),
                )
        except ReviewContextError as exc:
            raise provider_cli.core.PowerPackError(str(exc)) from exc

        user_prompt = provider_cli._prompt_from_args(args)
        if provider != provider_cli.PROVIDER_CODEX:
            user_prompt = _without_leading_github_mention(user_prompt)
        args.prompt = context_prompt + "\n\nUSER REVIEW INSTRUCTION\n" + user_prompt
        args.prompt_file = None

        requested_output = getattr(args, "output", None)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            original_cmd_review_run(args)
        rendered = captured.getvalue()
        if rendered:
            print(rendered, end="")

        review_text = rendered
        if requested_output:
            try:
                review_text = Path(requested_output).read_text(encoding="utf-8")
            except OSError:
                review_text = rendered

        blocked = _blocked_review_status(review_text)
        if blocked:
            raise provider_cli.core.PowerPackError(
                f"Web code review did not complete: {blocked}. The blocked reviewer response above is preserved as evidence."
            )

    def prepare_parser() -> argparse.ArgumentParser:
        parser = original_prepare_parser()
        root = provider_cli._subparsers(parser)
        review = root.choices["review"]
        run = provider_cli._subparsers(review).choices["run"]
        run.add_argument(
            "--pr",
            help="Required for Web review: GitHub PR number or canonical PR URL",
        )
        run.add_argument(
            "--github-plugin-authorized",
            action="store_true",
            help=(
                "Required attestation that the GitHub app/plugin is installed and connected in ChatGPT Web/Desktop and authorized for this repository; Web prompts invoke @GitHub automatically"
            ),
        )
        run.set_defaults(func=cmd_review_run)
        return parser

    provider_cli.cmd_review_run = cmd_review_run
    provider_cli._prepare_parser = prepare_parser
