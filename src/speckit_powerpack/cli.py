from __future__ import annotations

import argparse
from importlib import resources
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

from . import __version__
from .backend_compat import install_backend_compat
from .browserless_review import BrowserlessReviewError, run_browserless_code_review
from .chatgpt_project_provider import (
    ChatGPTBackendClient,
    ChatGPTProject,
    ChatGPTProjectError,
    load_codex_auth,
)
from .github_connector_discovery import GitHubConnectorDiscoveryError, discover_github_connector
from .update_manager import UpdateError, apply_self_update, check_update, effective_source


install_backend_compat()

PRODUCT_NAME = "Specify PowerPack"
CANONICAL_CLI = "specify-powerpack"
SPECKIT_REPO = "https://github.com/github/spec-kit.git"
SPECKIT_TESTED_TAG = "v1.0.4"
SPECKIT_MIN_VERSION = (1, 0, 0)
SPECKIT_MIN_VERSION_TEXT = "1.0.0"
DEFAULT_INTEGRATION = "codex"
_VERSION_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)")


class PowerPackError(RuntimeError):
    pass


def run(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        raise PowerPackError((proc.stderr or proc.stdout or "command failed").strip())
    return proc


def asset(relative: str):
    return resources.as_file(resources.files("speckit_powerpack").joinpath("assets", relative))


def write_json(path: Path, data: Any, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_asset_json(relative: str) -> dict[str, Any]:
    with asset(relative) as source:
        value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PowerPackError(f"Packaged config {relative} must contain an object.")
    return value


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(value or "")
    return tuple(int(part) for part in match.groups()) if match else None


def specify_version(binary: str) -> str | None:
    machine = run([binary, "version", "--features", "--json"], check=False)
    if machine.returncode == 0:
        try:
            payload = json.loads(machine.stdout)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and payload.get("version"):
            return str(payload["version"])
    human = run([binary, "version"], check=False)
    match = _VERSION_RE.search(f"{human.stdout}\n{human.stderr}")
    return match.group(0) if match else None


def spec_kit_compatible(version: str | None) -> bool:
    parsed = parse_version(version or "")
    return parsed is not None and parsed >= SPECKIT_MIN_VERSION


def install_tested_spec_kit() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise PowerPackError("uv is required to bootstrap official GitHub Spec Kit.")
    run([uv, "tool", "install", "--force", f"git+{SPECKIT_REPO}@{SPECKIT_TESTED_TAG}"])
    binary = shutil.which("specify")
    if not binary:
        raise PowerPackError("Spec Kit was installed but 'specify' is not visible on PATH. Restart the shell or fix uv tool PATH.")
    version = specify_version(binary)
    if not spec_kit_compatible(version):
        raise PowerPackError(f"Installed Spec Kit {version or 'unknown'} is incompatible.")
    return binary


def ensure_specify(*, bootstrap: bool) -> str:
    binary = shutil.which("specify")
    if binary:
        version = specify_version(binary)
        if spec_kit_compatible(version):
            return binary
        if not bootstrap:
            raise PowerPackError(
                f"Spec Kit {version or 'unknown'} is incompatible; {PRODUCT_NAME} requires >= {SPECKIT_MIN_VERSION_TEXT}."
            )
    elif not bootstrap:
        raise PowerPackError("Official Spec Kit CLI ('specify') is missing. Re-run with --bootstrap-speckit.")
    return install_tested_spec_kit()


def _review_config(project: Path) -> tuple[Path, dict[str, Any]]:
    path = project / ".specify" / "powerpack" / "review.json"
    if not path.is_file():
        raise PowerPackError(f"PowerPack review config is missing. Run '{CANONICAL_CLI} install .' first.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PowerPackError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PowerPackError("PowerPack review config must contain an object.")
    return path, data


def _migrate_review_config(project: Path, *, reset: bool) -> None:
    path = project / ".specify" / "powerpack" / "review.json"
    default = read_asset_json("config/default-review.json")
    if reset or not path.is_file():
        write_json(path, default, overwrite=True)
        return
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        old = {}
    if not isinstance(old, dict):
        old = {}
    old_project = old.get("chatgpt_project") if isinstance(old.get("chatgpt_project"), dict) else {}
    legacy = old.get("chatgpt_web") if isinstance(old.get("chatgpt_web"), dict) else {}
    source = old_project or legacy
    project_id = str(source.get("project_id") or "").strip()
    project_name = str(source.get("project_name") or "").strip()
    project_url = str(source.get("project_url") or "").strip()
    if project_id.startswith("g-p-") and project_name:
        default["provider"] = "chatgpt-project"
        target = default["chatgpt_project"]
        target.update({
            "project_id": project_id,
            "project_name": project_name,
            "project_url": project_url or None,
            "authorization": "codex-backend-api",
        })
    write_json(path, default, overwrite=True)


def install_support(project: Path, integration: str, *, reset_config: bool = False) -> None:
    base = project / ".specify" / "powerpack"
    bin_dir = base / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    runtime_assets = {
        "runtime/powerpack_runtime.py": "powerpack.py",
        "runtime/powerpack_capabilities.py": "capabilities.py",
        "runtime/powerpack_review_protocol.py": "review_protocol.py",
    }
    for source_name, dest_name in runtime_assets.items():
        with asset(source_name) as source:
            dest = bin_dir / dest_name
            shutil.copy2(source, dest)
            if os.name != "nt":
                dest.chmod(0o755)
    for source_name, dest_name in {
        "review/deep-review-protocol.md": "deep-review-protocol.md",
    }.items():
        with asset(source_name) as source:
            shutil.copy2(source, base / dest_name)

    routing = read_asset_json("config/default-model-routing.json")
    routing["active_integration"] = integration
    write_json(base / "model-routing.json", routing, overwrite=reset_config)
    _migrate_review_config(project, reset=reset_config)
    for config, filename in (
        ("config/default-update.json", "update.json"),
    ):
        write_json(base / filename, read_asset_json(config), overwrite=reset_config)
    write_json(base / "prerequisites.json", {
        "schema_version": 2,
        "mode": "strict",
        "steps": {
            "implement-review": [{"check": "implementation-evidence"}],
        },
    }, overwrite=reset_config)
    write_json(base / "quality-gates.json", {
        "schema_version": 1,
        "policy": "capability-strategy",
        "custom_command": None,
        "unknown_architecture": "block",
        "ambiguous_architecture": "block",
    }, overwrite=reset_config)
    ignore = base / ".gitignore"
    if not ignore.exists():
        ignore.write_text("runtime/\nreviews/\n*.local.json\n", encoding="utf-8")


def install_components(project: Path, specify: str) -> None:
    with asset("extensions/powerpack-tools") as ext:
        run([specify, "extension", "add", str(ext), "--dev", "--force", "--priority", "5"], cwd=project)
    run([specify, "preset", "remove", "powerpack-core"], cwd=project, check=False)
    with asset("presets/powerpack-core") as preset:
        run([specify, "preset", "add", "--dev", str(preset), "--priority", "5"], cwd=project)


def install_powerpack(
    path: str,
    integration: str,
    *,
    initialize: bool,
    bootstrap: bool,
    reset_config: bool = False,
) -> Path:
    project = Path(path).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    specify = ensure_specify(bootstrap=bootstrap)
    if initialize and not (project / ".specify").is_dir():
        run([specify, "init", "--here", "--integration", integration, "--force"], cwd=project)
    if not (project / ".specify").is_dir():
        raise PowerPackError(
            f"Target is not an initialized Spec Kit project. Use '{CANONICAL_CLI} init <path>' for first installation."
        )
    install_support(project, integration, reset_config=reset_config)
    install_components(project, specify)
    return project


def _project_candidates() -> list[ChatGPTProject]:
    try:
        projects = ChatGPTBackendClient().list_projects(limit=50)
    except ChatGPTProjectError as exc:
        raise PowerPackError(str(exc)) from exc
    return projects


def _select_project(projects: list[ChatGPTProject], selector: str | None, index: int | None) -> ChatGPTProject:
    if not projects:
        raise PowerPackError("No ChatGPT Projects were discovered for the Codex-authenticated account.")
    if selector:
        exact = [item for item in projects if item.id == selector or item.name.casefold() == selector.casefold() or item.url == selector]
        if len(exact) == 1:
            return exact[0]
        partial = [item for item in projects if selector.casefold() in item.name.casefold()]
        if len(partial) == 1:
            return partial[0]
        raise PowerPackError(f"Could not uniquely match ChatGPT Project: {selector}")
    if index is not None:
        if not (1 <= index <= len(projects)):
            raise PowerPackError("Project index is out of range.")
        return projects[index - 1]
    for number, item in enumerate(projects, start=1):
        print(f"{number:2}. {item.name} | {item.id} | {item.url}")
    if not sys.stdin.isatty():
        raise PowerPackError("Non-interactive setup requires --project or --index.")
    raw = input("Select ChatGPT Project number: ").strip()
    if not raw.isdigit():
        raise PowerPackError("Project selection must be numeric.")
    return _select_project(projects, None, int(raw))


def _persist_project_binding(project: Path, candidate: ChatGPTProject) -> None:
    path, data = _review_config(project)
    data["schema_version"] = max(5, int(data.get("schema_version", 0) or 0))
    data["provider"] = "chatgpt-project"
    target = data.setdefault("chatgpt_project", {})
    target.update({
        "required": True,
        "project_id": candidate.id,
        "project_name": candidate.name,
        "project_url": candidate.url,
        "authorization": "codex-backend-api",
        "context_mode": "serialized",
    })
    data.pop("chatgpt_web", None)
    write_json(path, data, overwrite=True)


def cmd_init(args: argparse.Namespace) -> None:
    project = install_powerpack(
        args.path,
        args.integration,
        initialize=True,
        bootstrap=True,
        reset_config=args.reset_config,
    )
    print(f"{PRODUCT_NAME} {__version__} installed in {project}.")
    print(
        "Next: run 'codex login', connect the GitHub App in ChatGPT/Codex, then "
        f"'{CANONICAL_CLI} review setup --path .'."
    )


def cmd_install(args: argparse.Namespace) -> None:
    project = install_powerpack(
        args.path,
        args.integration,
        initialize=False,
        bootstrap=args.bootstrap_speckit,
        reset_config=args.reset_config,
    )
    print(f"{PRODUCT_NAME} {__version__} materialized in {project}.")


def cmd_update(args: argparse.Namespace) -> None:
    project = Path(args.path).expanduser().resolve()
    if args.check:
        print(json.dumps(check_update(), ensure_ascii=False, indent=2))
        return
    if not args.project_only:
        source = effective_source()
        ref = args.ref or str(source["ref"])
        repository = args.repository or str(source["repository"])
        apply_self_update(repository, ref)
        print(f"{PRODUCT_NAME} CLI updated from {repository}@{ref}.")
    integration = args.integration or project_integration(project)
    install_powerpack(
        str(project),
        integration,
        initialize=False,
        bootstrap=args.bootstrap_speckit,
        reset_config=args.reset_config,
    )
    print("Project assets refreshed.")


def project_integration(project: Path) -> str:
    path = project / ".specify" / "powerpack" / "model-routing.json"
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("active_integration")
        except (OSError, json.JSONDecodeError):
            value = None
        if value in {"codex", "claude"}:
            return str(value)
    return DEFAULT_INTEGRATION


def _review_ready(project: Path, *, live: bool) -> dict[str, bool]:
    checks = {
        "codex-cli": bool(shutil.which("codex")),
        "codex-auth": False,
        "chatgpt-project-binding": False,
        "github-app": False,
    }
    try:
        load_codex_auth()
        checks["codex-auth"] = True
    except ChatGPTProjectError:
        pass
    try:
        _, data = _review_config(project)
        binding = data.get("chatgpt_project") if isinstance(data.get("chatgpt_project"), dict) else {}
        checks["chatgpt-project-binding"] = bool(
            data.get("provider") == "chatgpt-project"
            and str(binding.get("project_id") or "").startswith("g-p-")
            and binding.get("authorization") == "codex-backend-api"
        )
    except PowerPackError:
        pass
    if live and checks["codex-auth"]:
        try:
            state = discover_github_connector(ChatGPTBackendClient())
            checks["github-app"] = bool(state.ok)
        except (ChatGPTProjectError, GitHubConnectorDiscoveryError):
            checks["github-app"] = False
    elif not live:
        checks["github-app"] = checks["codex-auth"]
    return checks


def cmd_doctor(args: argparse.Namespace) -> None:
    project = Path(args.path).expanduser().resolve()
    hard = {
        "specify": bool(shutil.which("specify")),
        "spec-kit-project": (project / ".specify").is_dir(),
        "powerpack-runtime": (project / ".specify" / "powerpack" / "bin" / "powerpack.py").is_file(),
        "selected-executor": bool(shutil.which(project_integration(project))),
    }
    review = _review_ready(project, live=bool(args.strict_review))
    for key, value in {**hard, **review}.items():
        print(f"{'OK' if value else 'FAIL':5} {key}")
    if not all(hard.values()):
        raise PowerPackError(f"{PRODUCT_NAME} installation checks failed.")
    if args.strict_review and not all(review.values()):
        raise PowerPackError("Browserless Project/GitHub review is not ready.")


def cmd_review_setup(args: argparse.Namespace) -> None:
    project = Path(args.path).expanduser().resolve()
    _review_config(project)
    try:
        auth = load_codex_auth()
        client = ChatGPTBackendClient(auth.auth_path)
        client.validate_auth()
    except ChatGPTProjectError as exc:
        raise PowerPackError(str(exc)) from exc
    projects = _project_candidates()
    candidate = _select_project(projects, args.project, args.index)
    _persist_project_binding(project, candidate)
    print(f"Repository linked to ChatGPT Project '{candidate.name}' ({candidate.id}).")
    try:
        github = discover_github_connector(client, locale=args.locale)
    except GitHubConnectorDiscoveryError as exc:
        raise PowerPackError(
            "Project binding was saved, but the GitHub App is not ready for code review: " + str(exc)
        ) from exc
    print("GitHub App: READY" if github.ok else "GitHub App: NOT READY")
    print("Transport: browserless Codex Apps MCP; no Chrome, CDP, Playwright or Web2API.")


def cmd_project_discover(args: argparse.Namespace) -> None:
    try:
        load_codex_auth()
    except ChatGPTProjectError as exc:
        raise PowerPackError(str(exc)) from exc
    for number, item in enumerate(_project_candidates(), start=1):
        print(f"{number:2}. {item.name} | {item.id} | {item.url}")


def cmd_review_status(args: argparse.Namespace) -> None:
    project = Path(args.path).expanduser().resolve()
    path, data = _review_config(project)
    binding = data.get("chatgpt_project") if isinstance(data.get("chatgpt_project"), dict) else {}
    payload: dict[str, Any] = {
        "review_config": str(path),
        "provider": data.get("provider"),
        "backend": data.get("review_backend"),
        "project": {
            "id": binding.get("project_id"),
            "name": binding.get("project_name"),
            "url": binding.get("project_url"),
            "context_mode": binding.get("context_mode"),
        },
        "browserless": True,
        "readiness": _review_ready(project, live=args.live),
    }
    if args.live and payload["readiness"]["codex-auth"]:
        try:
            payload["github"] = discover_github_connector(ChatGPTBackendClient(), locale=args.locale).safe_report()
        except (ChatGPTProjectError, GitHubConnectorDiscoveryError) as exc:
            payload["github"] = {"ok": False, "error": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return "Perform the complete Deep Review Evidence Protocol for this implementation."


def cmd_review_run(args: argparse.Namespace) -> None:
    project = Path(args.path).expanduser().resolve()
    previous = Path(args.previous).expanduser().resolve() if args.previous else None
    output = Path(args.output).expanduser().resolve() if args.output else None
    try:
        result = run_browserless_code_review(
            project_path=project,
            pull_request=args.pr,
            prompt=_prompt(args),
            output=output,
            previous=previous,
            model=args.model,
            effort=args.effort,
            timeout=args.timeout,
            max_project_conversations=args.max_conversations,
            locale=args.locale,
        )
    except (BrowserlessReviewError, ChatGPTProjectError, GitHubConnectorDiscoveryError) as exc:
        raise PowerPackError(str(exc)) from exc
    print(json.dumps({
        "ok": True,
        "classification": "BROWSERLESS_CODE_REVIEW_COMPLETED",
        "verdict": result.review.get("verdict"),
        "output": str(result.output_path),
        "snapshot": result.snapshot.as_dict(),
        "project": {"id": result.project.project_id, "name": result.project.project_name},
        "snapshot_tools": list(result.snapshot_tools),
        "review_tools": list(result.github_tools),
        "browser_used": False,
        "cdp_used": False,
        "playwright_used": False,
        "web2api_used": False,
    }, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=CANONICAL_CLI)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help=f"Initialize Spec Kit when needed and install {PRODUCT_NAME} into a project")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--integration", choices=["codex", "claude"], default=DEFAULT_INTEGRATION)
    init.add_argument("--reset-config", action="store_true")
    init.set_defaults(func=cmd_init)

    install = sub.add_parser("install", help=f"Install/refresh {PRODUCT_NAME} in an existing Spec Kit project")
    install.add_argument("path", nargs="?", default=".")
    install.add_argument("--integration", choices=["codex", "claude"], default=DEFAULT_INTEGRATION)
    install.add_argument("--bootstrap-speckit", action="store_true")
    install.add_argument("--reset-config", action="store_true")
    install.set_defaults(func=cmd_install)

    update = sub.add_parser("update", help="Update the CLI and/or rematerialize project assets")
    update.add_argument("path", nargs="?", default=".")
    update.add_argument("--check", action="store_true")
    update.add_argument("--project-only", action="store_true")
    update.add_argument("--reset-config", action="store_true")
    update.add_argument("--repository")
    update.add_argument("--ref")
    update.add_argument("--integration", choices=["codex", "claude"])
    update.add_argument("--bootstrap-speckit", action="store_true")
    update.set_defaults(func=cmd_update)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("path", nargs="?", default=".")
    doctor.add_argument("--strict-review", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    review = sub.add_parser("review")
    rsub = review.add_subparsers(dest="review_command", required=True)
    setup = rsub.add_parser("setup", help="Bind this repository to a ChatGPT Project and verify the GitHub App")
    setup.add_argument("--path", default=".")
    setup.add_argument("--project", help="Project id, exact/unique name or URL")
    setup.add_argument("--index", type=int)
    setup.add_argument("--locale", default="pt-BR")
    setup.set_defaults(func=cmd_review_setup)

    status = rsub.add_parser("status")
    status.add_argument("--path", default=".")
    status.add_argument("--live", action="store_true")
    status.add_argument("--locale", default="pt-BR")
    status.set_defaults(func=cmd_review_status)

    project = rsub.add_parser("project")
    psub = project.add_subparsers(dest="project_command", required=True)
    discover = psub.add_parser("discover")
    discover.set_defaults(func=cmd_project_discover)

    review_run = rsub.add_parser("run", help="Review one exact GitHub PR with Project context + GitHub Codex App")
    review_run.add_argument("--path", default=".")
    review_run.add_argument("--pr", required=True, help="GitHub PR number or canonical PR URL")
    review_run.add_argument("--prompt")
    review_run.add_argument("--prompt-file")
    review_run.add_argument("--previous")
    review_run.add_argument("--output")
    review_run.add_argument("--model", default="gpt-5.6-sol")
    review_run.add_argument("--effort", default="xhigh")
    review_run.add_argument("--timeout", type=int, default=600)
    review_run.add_argument("--max-conversations", type=int, default=2)
    review_run.add_argument("--locale", default="pt-BR")
    review_run.set_defaults(func=cmd_review_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        return 0
    except (PowerPackError, UpdateError, BrowserlessReviewError, ChatGPTProjectError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
