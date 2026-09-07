from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from . import cli as core
from . import cli_account_binding as legacy
from .chatgpt_project_provider import (
    ChatGPTBackendClient,
    ChatGPTProject,
    ChatGPTProjectError,
    load_codex_auth,
    project_id_from_url_or_id,
    run_codex_cli_review,
    run_project_review,
)


AUTH_SOURCE = "codex-auth-json"
PROJECT_AUTH = "codex-backend-api"
PROVIDER_CODEX = "codex"
PROVIDER_PROJECT = "chatgpt-project"


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise core.PowerPackError("Internal CLI error: subparser registry not found")


def _review_path(project: Path) -> Path:
    return project / ".specify" / "powerpack" / "review.json"


def _read_review(project: Path) -> tuple[Path, dict[str, Any]]:
    path = _review_path(project)
    if not path.is_file():
        raise core.PowerPackError("PowerPack review config is missing; install/refresh PowerPack first.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise core.PowerPackError(f"Cannot read PowerPack review config: {exc}") from exc
    if not isinstance(data, dict):
        raise core.PowerPackError("PowerPack review config must contain an object.")
    return path, data


def _persist_auth() -> dict[str, Any]:
    try:
        auth = load_codex_auth()
        client = ChatGPTBackendClient(auth.auth_path)
        me = client.validate_auth()
    except ChatGPTProjectError as exc:
        raise core.PowerPackError(str(exc)) from exc
    path, data = core.global_config()
    platform = core.platform_key()
    data["schema_version"] = max(4, int(data.get("schema_version", 0) or 0))
    data.setdefault("codex_auth", {})[platform] = {
        "source": AUTH_SOURCE,
        "auth_path": str(auth.auth_path),
        "account_id": auth.account_id,
    }
    # Compatibility record for tooling that still expects an account registry.
    data.setdefault("accounts", {}).setdefault(platform, {})["codex"] = {
        "source": AUTH_SOURCE,
        "auth_path": str(auth.auth_path),
        "account_id": auth.account_id,
        "account_label": _account_label(me) or "Codex ChatGPT account",
    }
    data.setdefault("active_profiles", {})[platform] = "codex"
    core.save_global(path, data)
    return {"auth": auth, "me": me}


def _account_label(me: dict[str, Any]) -> str | None:
    for key in ("email", "name", "username"):
        value = me.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    account = me.get("account")
    if isinstance(account, dict):
        for key in ("email", "name"):
            value = account.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _auth_ready() -> bool:
    try:
        load_codex_auth()
        return True
    except ChatGPTProjectError:
        return False


def _set_provider(project: Path, provider: str, bound: dict[str, Any] | None = None) -> None:
    path, review = _read_review(project)
    review["provider"] = provider
    web = review.setdefault("chatgpt_web", {})
    if provider == PROVIDER_PROJECT and bound:
        web["required"] = True
        web["enabled"] = True
        web["mode"] = "backend-api"
        web["project_alias"] = bound["alias"]
        web["project_id"] = bound["project_id"]
        web["project_name"] = bound["project_name"]
        web["project_url"] = bound["project_url"]
        web["profile"] = "codex"
        web["account_label"] = bound.get("account_label") or "Codex ChatGPT account"
        web["profile_scope"] = "account"
        web["profile_platform"] = core.platform_key()
        web["authorization"] = PROJECT_AUTH
        web["headless"] = None
    else:
        web["required"] = False
        web["enabled"] = False
        web["mode"] = "disabled"
        for key in (
            "project_alias",
            "project_id",
            "project_name",
            "project_url",
            "account_label",
            "authorization",
        ):
            web[key] = None
        web["profile"] = "codex"
        web["profile_scope"] = "account"
        web["profile_platform"] = core.platform_key()
        web["headless"] = None
    core.write_json(path, review, overwrite=True)


def _persist_project(project_path: Path, candidate: ChatGPTProject, *, alias: str | None = None) -> dict[str, Any]:
    auth_info = _persist_auth()
    alias = alias or _slug(candidate.name or candidate.id)
    cfg_path, data = core.global_config()
    platform = core.platform_key()
    label = _account_label(auth_info["me"]) or "Codex ChatGPT account"
    registered = data.setdefault("projects", {}).setdefault(alias, {"bindings": {}})
    registered["display_name"] = candidate.name
    registered["project_id"] = candidate.id
    registered.setdefault("bindings", {})[platform] = {
        "project_id": candidate.id,
        "url": candidate.url,
        "profile": "codex",
        "account_label": label,
        "authorization": PROJECT_AUTH,
        "auth_source": AUTH_SOURCE,
    }
    core.save_global(cfg_path, data)
    bound = {
        "alias": alias,
        "project_id": candidate.id,
        "project_name": candidate.name,
        "project_url": candidate.url,
        "account_label": label,
    }
    _set_provider(project_path, PROVIDER_PROJECT, bound)
    return bound


def _slug(value: str) -> str:
    import re

    result = re.sub(r"[^a-z0-9]+", "-", (value or "project").casefold()).strip("-")
    return result[:64] or "project"


def _configured_binding(project: Path) -> dict[str, Any] | None:
    try:
        _, review = _read_review(project)
    except core.PowerPackError:
        return None
    web = review.get("chatgpt_web") if isinstance(review.get("chatgpt_web"), dict) else {}
    if review.get("provider") != PROVIDER_PROJECT:
        return None
    project_id = web.get("project_id") or web.get("project_url")
    if not project_id:
        return None
    try:
        normalized = project_id_from_url_or_id(str(project_id))
    except ChatGPTProjectError:
        return None
    return {
        "alias": web.get("project_alias"),
        "project_id": normalized,
        "project_name": web.get("project_name"),
        "project_url": web.get("project_url"),
        "authorization": web.get("authorization"),
    }


def review_readiness(project: Path) -> dict[str, bool]:
    try:
        _, review = _read_review(project)
    except core.PowerPackError:
        return {
            "codex-auth-json": False,
            "review-provider-configured": False,
            "chatgpt-project-binding": False,
        }
    provider = str(review.get("provider") or PROVIDER_CODEX)
    auth_ok = _auth_ready()
    binding = _configured_binding(project)
    project_ok = provider != PROVIDER_PROJECT or bool(
        binding and binding.get("authorization") == PROJECT_AUTH
    )
    return {
        "codex-auth-json": auth_ok,
        "review-provider-configured": provider in {PROVIDER_CODEX, PROVIDER_PROJECT},
        "chatgpt-project-binding": project_ok,
    }


def print_review_setup_status(project: Path) -> None:
    try:
        _, review = _read_review(project)
        provider = str(review.get("provider") or PROVIDER_CODEX)
    except core.PowerPackError:
        provider = "unconfigured"
    readiness = review_readiness(project)
    print("\nPOWERPACK REVIEW SETUP")
    print(f"Provider: {provider}")
    print(f"Codex auth: {'OK' if readiness['codex-auth-json'] else 'MISSING'} (~/.codex/auth.json)")
    if provider == PROVIDER_PROJECT:
        binding = _configured_binding(project)
        print(
            "ChatGPT Project: "
            + (f"{binding.get('project_name') or binding.get('project_id')} ({binding.get('project_id')})" if binding else "MISSING")
        )
        print("Transport: chatgpt.com/backend-api (no Playwright/browser required)")
    else:
        print("ChatGPT Project: not linked; reviews use Codex CLI/local repository context.")
    print("Run 'speckit-powerpack review setup --path .' to change the repository binding.\n")


def cmd_review_setup(args: argparse.Namespace) -> None:
    if getattr(args, "install_browser", False):
        raise core.PowerPackError("Browser installation is intentionally disabled: this PowerPack flow is browserless.")
    project = Path(getattr(args, "path", ".")).resolve()
    if not _review_path(project).is_file():
        raise core.PowerPackError("Target is not PowerPack-ready. Run 'speckit-powerpack install .' first.")
    auth_info = _persist_auth()
    print(f"Codex/ChatGPT authorization validated via {auth_info['auth'].auth_path}.")

    explicit_project = getattr(args, "project", None)
    if getattr(args, "no_project", False):
        wants_project = False
    elif explicit_project or getattr(args, "yes_project", False):
        wants_project = True
    else:
        if not sys.stdin.isatty():
            wants_project = False
        else:
            answer = input("Deseja vincular este repositório local a um ChatGPT Project existente? [y/N]: ").strip().casefold()
            wants_project = answer in {"y", "yes", "s", "sim"}

    if not wants_project:
        _set_provider(project, PROVIDER_CODEX)
        print("Repository configured with CodexProvider (no ChatGPT Project binding).")
        return

    client = ChatGPTBackendClient()
    projects = client.list_projects()
    if not projects:
        raise core.PowerPackError("No ChatGPT Projects were returned by the authenticated account.")
    candidate = _resolve_candidate(projects, explicit_project, getattr(args, "index", None))
    bound = _persist_project(project, candidate, alias=getattr(args, "alias", None))
    print(
        f"Repository linked to ChatGPT Project '{bound['project_name']}' ({bound['project_id']}) using ChatGPTProjectProvider."
    )


def _resolve_candidate(projects: list[ChatGPTProject], selector: str | None, index: int | None) -> ChatGPTProject:
    if selector:
        try:
            project_id = project_id_from_url_or_id(selector)
        except ChatGPTProjectError:
            project_id = ""
        if project_id:
            for candidate in projects:
                if candidate.id == project_id:
                    return candidate
        exact = [item for item in projects if item.name.casefold() == selector.casefold()]
        if len(exact) == 1:
            return exact[0]
        partial = [item for item in projects if selector.casefold() in item.name.casefold()]
        if len(partial) == 1:
            return partial[0]
        raise core.PowerPackError(f"Could not uniquely match ChatGPT Project: {selector}")
    if index is not None:
        if index < 1 or index > len(projects):
            raise core.PowerPackError("Project selection index is out of range.")
        return projects[index - 1]
    for number, item in enumerate(projects, start=1):
        print(f"{number:2}. {item.name} | {item.id} | {item.url}")
    if not sys.stdin.isatty():
        raise core.PowerPackError("Project selection requires --project or --index in non-interactive mode.")
    raw = input("Select Project number: ").strip()
    if not raw.isdigit():
        raise core.PowerPackError("Project selection must be numeric.")
    return _resolve_candidate(projects, None, int(raw))


def cmd_auth_authorize(args: argparse.Namespace) -> None:
    info = _persist_auth()
    label = _account_label(info["me"]) or getattr(args, "account_label", None) or "Codex ChatGPT account"
    print(f"Authorized ChatGPT account through ~/.codex/auth.json: {label}")
    print("No browser profile, cookie copy, Playwright or Chromium is used.")


def cmd_auth_list(args: argparse.Namespace) -> None:
    try:
        auth = load_codex_auth()
    except ChatGPTProjectError:
        print("No usable ~/.codex/auth.json found.")
        return
    print(f"* codex: source={AUTH_SOURCE} account_id={auth.account_id} auth_path={auth.auth_path}")


def cmd_auth_use(args: argparse.Namespace) -> None:
    if args.profile != "codex":
        raise core.PowerPackError("Browserless mode exposes a single profile named 'codex', backed by ~/.codex/auth.json.")
    _persist_auth()
    print("Active review identity is the ChatGPT account authenticated by Codex CLI.")


def cmd_auth_reconfigure(args: argparse.Namespace) -> None:
    cmd_auth_authorize(args)


def cmd_auth_logout(args: argparse.Namespace) -> None:
    raise core.PowerPackError("PowerPack does not delete Codex credentials. Use 'codex logout' explicitly if you want to sign out.")


def cmd_auth_forget(args: argparse.Namespace) -> None:
    cfg_path, data = core.global_config()
    platform = core.platform_key()
    data.setdefault("codex_auth", {}).pop(platform, None)
    data.setdefault("accounts", {}).setdefault(platform, {}).pop("codex", None)
    core.save_global(cfg_path, data)
    print("Forgot PowerPack's local Codex-auth registration. ~/.codex/auth.json was not modified.")


def cmd_project_discover(args: argparse.Namespace) -> None:
    _persist_auth()
    try:
        projects = ChatGPTBackendClient().list_projects()
    except ChatGPTProjectError as exc:
        raise core.PowerPackError(str(exc)) from exc
    if not projects:
        print("No ChatGPT Projects discovered.")
        return
    for index, item in enumerate(projects, start=1):
        print(f"{index:2}. {item.name} | {item.id} | {item.url}")


def cmd_project_select(args: argparse.Namespace) -> None:
    if getattr(args, "manual", False):
        raise core.PowerPackError("--manual browser selection is disabled. Use --index, --project via review setup, or project add.")
    _persist_auth()
    projects = ChatGPTBackendClient().list_projects()
    candidate = _resolve_candidate(projects, None, args.index)
    bound = _persist_project(Path(args.path).resolve(), candidate, alias=args.alias)
    print(f"Bound repository to {bound['project_name']} ({bound['project_id']}).")


def cmd_project_add(args: argparse.Namespace) -> None:
    _persist_auth()
    try:
        candidate = ChatGPTBackendClient().get_project(args.url)
    except ChatGPTProjectError as exc:
        raise core.PowerPackError(str(exc)) from exc
    bound = _persist_project(Path(args.path).resolve(), candidate, alias=args.alias)
    print(f"Bound repository to {bound['project_name']} ({bound['project_id']}).")


def cmd_project_accept_invite(args: argparse.Namespace) -> None:
    # If the invite was already accepted by this ChatGPT account and the URL contains a g-p id,
    # binding works without a browser. Accepting a brand-new invitation itself is a Web UI action.
    try:
        cmd_project_add(args)
    except Exception as exc:
        raise core.PowerPackError(
            "This browserless provider cannot click a new ChatGPT invitation. Accept the invite once in ChatGPT Web, then rerun 'review project add <project-url>'. "
            f"Original error: {exc}"
        ) from exc


def cmd_project_bind(args: argparse.Namespace) -> None:
    namespace = argparse.Namespace(url=args.url, alias=args.alias, path=".")
    cmd_project_add(namespace)


def cmd_project_list(args: argparse.Namespace) -> None:
    _, data = core.global_config()
    platform = core.platform_key()
    for alias, item in sorted(data.get("projects", {}).items()):
        if not isinstance(item, dict):
            continue
        binding = item.get("bindings", {}).get(platform)
        if not isinstance(binding, dict):
            continue
        print(
            f"{alias}: name={item.get('display_name') or alias} project_id={binding.get('project_id')} "
            f"authorization={binding.get('authorization')} url={binding.get('url')}"
        )


def cmd_project_use(args: argparse.Namespace) -> None:
    project_path = Path(args.path).resolve()
    _, data = core.global_config()
    platform = core.platform_key()
    registered = data.get("projects", {}).get(args.alias)
    if not isinstance(registered, dict):
        raise core.PowerPackError(f"Unknown project alias: {args.alias}")
    binding = registered.get("bindings", {}).get(platform)
    if not isinstance(binding, dict) or binding.get("authorization") != PROJECT_AUTH:
        raise core.PowerPackError(f"Project '{args.alias}' has no browserless binding for {platform}.")
    bound = {
        "alias": args.alias,
        "project_id": binding.get("project_id") or project_id_from_url_or_id(str(binding.get("url") or "")),
        "project_name": registered.get("display_name") or args.alias,
        "project_url": binding.get("url"),
        "account_label": binding.get("account_label"),
    }
    _set_provider(project_path, PROVIDER_PROJECT, bound)
    print(f"Repository now uses ChatGPTProjectProvider with '{bound['project_name']}'.")


def cmd_doctor(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    specify_binary = shutil.which("specify")
    integration = core.project_integration(project)
    hard = {
        "specify": bool(specify_binary),
        "spec-kit-project": (project / ".specify").is_dir(),
        "powerpack-runtime": (project / ".specify" / "powerpack" / "bin" / "powerpack.py").is_file(),
        "selected-executor": bool(shutil.which(integration)),
    }
    ready = review_readiness(project)
    print(f"Platform:    {core.platform_key()}")
    print(f"Integration: {integration}")
    for key, value in {**hard, **ready}.items():
        print(f"{'OK' if value else 'FAIL':5} {key}")
    if not all(hard.values()):
        raise core.PowerPackError("PowerPack installation checks failed.")
    if getattr(args, "strict_review", False) and not all(ready.values()):
        print_review_setup_status(project)
        raise core.PowerPackError("Review provider is not ready.")
    if not all(ready.values()):
        print_review_setup_status(project)


def _prompt_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "prompt", None):
        return str(args.prompt)
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8")
    raise core.PowerPackError("Provide --prompt or --prompt-file.")


def _provider_for(project: Path, requested: str) -> str:
    if requested not in {"auto", "codex", "web", PROVIDER_PROJECT}:
        raise core.PowerPackError(f"Unsupported review provider: {requested}")
    if requested == "codex":
        return PROVIDER_CODEX
    if requested in {"web", PROVIDER_PROJECT}:
        return PROVIDER_PROJECT
    _, review = _read_review(project)
    return str(review.get("provider") or PROVIDER_CODEX)


def _project_target(project: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    binding = _configured_binding(project)
    if not binding:
        raise core.PowerPackError("This repository is not linked to a ChatGPT Project. Run 'review setup' first.")
    return str(binding["project_id"])


def cmd_review_run(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    prompt = _prompt_from_args(args)
    provider = _provider_for(project, args.provider)
    try:
        if provider == PROVIDER_CODEX:
            result = run_codex_cli_review(prompt=prompt, cwd=project, timeout=args.timeout)
        else:
            result = run_project_review(
                prompt=prompt,
                project_id_or_url=_project_target(project, args.project),
                model=args.model,
                effort=args.effort,
                max_conversations=args.max_conversations,
            )
    except ChatGPTProjectError as exc:
        raise core.PowerPackError(str(exc)) from exc
    if args.output:
        Path(args.output).write_text(result.text + "\n", encoding="utf-8")
    else:
        print(result.text)


def _smoke_prompt(marker: str) -> str:
    return f"""This is an integration smoke test for a code-review provider.
Review the following Python code as read-only code review:

```python
def ratio(total, count):
    return total / count
```

Identify at least one concrete correctness risk. Do not propose unrelated refactors.
Finish your response with this exact marker on its own line:
{marker}
"""


def cmd_review_smoke(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    flows = [args.flow] if args.flow != "both" else ["cli", "web"]
    report: dict[str, Any] = {"ok": True, "flows": {}}
    for flow in flows:
        marker = "POWERPACK_SMOKE_CLI_OK" if flow == "cli" else "POWERPACK_SMOKE_WEB_OK"
        try:
            if flow == "cli":
                result = run_codex_cli_review(prompt=_smoke_prompt(marker), cwd=project, timeout=args.timeout)
            else:
                result = run_project_review(
                    prompt=_smoke_prompt(marker),
                    project_id_or_url=_project_target(project, args.project),
                    model=args.model,
                    effort=args.effort,
                    max_conversations=min(args.max_conversations, 2),
                )
            ok = marker in result.text and "zero" in result.text.casefold() or marker in result.text and "division" in result.text.casefold()
            report["flows"][flow] = {
                "ok": bool(ok),
                "provider": result.provider,
                "project_id": result.project_id,
                "response_id": result.response_id,
                "marker": marker,
                "response_preview": result.text[:500],
            }
            if not ok:
                report["ok"] = False
        except Exception as exc:
            report["ok"] = False
            report["flows"][flow] = {"ok": False, "error": str(exc), "marker": marker}
    smoke_dir = project / ".specify" / "powerpack" / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    report_path = smoke_dir / "code-review.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise core.PowerPackError(f"Code-review smoke failed. See {report_path}")


def _prepare_parser() -> argparse.ArgumentParser:
    # Real CLI installs must never install or launch Playwright/Chromium.
    core.ensure_playwright_browser = lambda: None
    core.review_readiness = review_readiness
    core.print_review_setup_status = print_review_setup_status

    parser = legacy.build_parser()
    root = _subparsers(parser)
    root.choices["doctor"].set_defaults(func=cmd_doctor)

    review = root.choices["review"]
    rsub = _subparsers(review)
    setup = rsub.choices["setup"]
    setup.add_argument("--path", default=".")
    setup.add_argument("--yes-project", action="store_true", help="Link this repository to a ChatGPT Project")
    setup.add_argument("--no-project", action="store_true", help="Use CodexProvider without a ChatGPT Project")
    setup.add_argument("--project", help="Project id, URL or unique name")
    setup.add_argument("--index", type=int)
    setup.add_argument("--alias")
    setup.set_defaults(func=cmd_review_setup)

    # Keep the old shape usable, but make it browserless.
    rsub.choices["authorize"].set_defaults(func=lambda args: cmd_project_add(argparse.Namespace(url=args.url, alias=args.project, path=args.path)))

    auth = rsub.choices["auth"]
    asub = _subparsers(auth)
    asub.choices["authorize"].set_defaults(func=cmd_auth_authorize)
    asub.choices["list"].set_defaults(func=cmd_auth_list)
    asub.choices["use"].set_defaults(func=cmd_auth_use)
    asub.choices["reconfigure"].set_defaults(func=cmd_auth_reconfigure)
    asub.choices["logout"].set_defaults(func=cmd_auth_logout)
    asub.choices["forget"].set_defaults(func=cmd_auth_forget)

    project = rsub.choices["project"]
    psub = _subparsers(project)
    psub.choices["discover"].set_defaults(func=cmd_project_discover)
    psub.choices["select"].set_defaults(func=cmd_project_select)
    psub.choices["add"].set_defaults(func=cmd_project_add)
    psub.choices["accept-invite"].set_defaults(func=cmd_project_accept_invite)
    psub.choices["bind"].set_defaults(func=cmd_project_bind)
    psub.choices["list"].set_defaults(func=cmd_project_list)
    psub.choices["use"].set_defaults(func=cmd_project_use)

    run = rsub.add_parser("run", help="Run one independent code review through Codex or ChatGPT Project context")
    run.add_argument("--provider", choices=["auto", "codex", "web", PROVIDER_PROJECT], default="auto")
    run.add_argument("--path", default=".")
    run.add_argument("--project")
    run.add_argument("--prompt")
    run.add_argument("--prompt-file")
    run.add_argument("--output")
    run.add_argument("--model", default="gpt-5.6-sol")
    run.add_argument("--effort", default="high")
    run.add_argument("--max-conversations", type=int, default=6)
    run.add_argument("--timeout", type=int, default=300)
    run.set_defaults(func=cmd_review_run)

    smoke = rsub.add_parser("smoke", help="E2E smoke test for CLI and ChatGPT Project review paths")
    smoke.add_argument("--flow", choices=["cli", "web", "both"], default="both")
    smoke.add_argument("--path", default=".")
    smoke.add_argument("--project")
    smoke.add_argument("--model", default="gpt-5.6-sol")
    smoke.add_argument("--effort", default="high")
    smoke.add_argument("--max-conversations", type=int, default=2)
    smoke.add_argument("--timeout", type=int, default=300)
    smoke.set_defaults(func=cmd_review_smoke)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _prepare_parser()
    args = parser.parse_args(argv)
    if getattr(args, "yes_project", False) and getattr(args, "no_project", False):
        print("ERROR: --yes-project and --no-project are mutually exclusive", file=sys.stderr)
        return 2
    try:
        args.func(args)
        return 0
    except (core.PowerPackError, core.UpdateError, ChatGPTProjectError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


# Ensure direct imports of the legacy command module during this process see the new readiness contract.
legacy.review_readiness = review_readiness
legacy.print_review_setup_status = print_review_setup_status
