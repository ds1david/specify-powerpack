from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request

POWERPACK_VERSION = "0.4.0"
MIN_SPECKIT = (1, 0, 0)
BACKEND_API = "https://chatgpt.com/backend-api"


def _run(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_project(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return None


def _semver(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return tuple(int(match.group(i)) for i in (1, 2, 3))


def _account_id(token: str) -> str:
    parts = token.split(".")
    if len(parts) < 2:
        return ""
    try:
        body = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(body.encode()).decode("utf-8"))
    except Exception:
        return ""
    auth = claims.get("https://api.openai.com/auth") if isinstance(claims, dict) else None
    return str(auth.get("chatgpt_account_id") or "") if isinstance(auth, dict) else ""


def _codex_auth() -> tuple[str, str]:
    path = Path.home() / ".codex" / "auth.json"
    payload = _json(path)
    tokens = payload.get("tokens") if isinstance(payload, dict) else None
    if not isinstance(tokens, dict):
        raise RuntimeError("~/.codex/auth.json has no tokens object")
    token = str(tokens.get("access_token") or "").strip()
    account = str(tokens.get("account_id") or "").strip() or _account_id(token)
    if not token or not account:
        raise RuntimeError("Codex authentication is incomplete")
    return token, account


def _request(token: str, account: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        BACKEND_API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "ChatGPT-Account-ID": account,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"specify-powerpack/{POWERPACK_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ChatGPT backend HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"cannot reach ChatGPT backend: {exc.reason}") from exc
    return json.loads(raw) if raw.strip() else {}


def _feature_dir(project: Path, target: str) -> tuple[Path | None, str]:
    raw = os.environ.get("SPECIFY_FEATURE_DIRECTORY", "").strip()
    source = "SPECIFY_FEATURE_DIRECTORY"
    if not raw:
        marker = project / ".specify" / "feature.json"
        if marker.is_file():
            try:
                raw = str((_json(marker) or {}).get("feature_directory") or "").strip()
            except Exception as exc:
                return None, f"invalid .specify/feature.json: {exc}"
            source = ".specify/feature.json"
    if not raw and target:
        raw = target[6:] if target.startswith("specs/") else target
        source = "target"
        direct = project / "specs" / raw
        if direct.is_dir():
            raw = str(direct)
        else:
            matches = [p.parent for p in (project / "specs").rglob("spec.md") if p.parent.name == raw] if (project / "specs").is_dir() else []
            if len(matches) == 1:
                raw = str(matches[0])
            elif len(matches) > 1:
                return None, f"target {target!r} is ambiguous"
    if not raw:
        return None, "no active feature selected"
    path = Path(raw)
    if not path.is_absolute():
        path = project / path
    try:
        resolved = path.resolve()
        resolved.relative_to((project / "specs").resolve())
    except (OSError, ValueError):
        return None, f"{source} points outside specs/"
    if not resolved.is_dir():
        return None, f"{source} points to missing directory {resolved}"
    return resolved, source


_TASK_PLAN_TASK_RE = re.compile(
    r"^\\s*-\\s*\\[(?P<mark>[ xX])\\]\\s+(?P<id>T\\d{3,})\\s+(?P<rest>.+?)\\s*$"
)
_TASK_PLAN_PHASE_RE = re.compile(
    r"^##\\s+Phase\\s+(?P<number>\\d+)\\s*:\\s*(?P<name>.+?)\\s*$",
    re.IGNORECASE,
)


def _task_plan_summary(feature: Path) -> dict[str, Any]:
    plan = feature / "plan.md"
    tasks = feature / "tasks.md"
    if not plan.is_file():
        raise RuntimeError("tasks.md exists but plan.md is missing")
    if not tasks.is_file():
        raise RuntimeError("tasks.md is missing")

    phases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    phase_numbers: list[int] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    outside: list[str] = []

    for line in tasks.read_text(encoding="utf-8", errors="replace").splitlines():
        phase = _TASK_PLAN_PHASE_RE.match(line)
        if phase:
            current = {
                "number": int(phase.group("number")),
                "name": phase.group("name").strip(),
                "total": 0,
                "completed": 0,
                "pending": 0,
                "parallel": 0,
            }
            phases.append(current)
            phase_numbers.append(current["number"])
            continue

        task = _TASK_PLAN_TASK_RE.match(line)
        if not task:
            continue
        task_id = task.group("id")
        if task_id in seen:
            duplicates.append(task_id)
        seen.add(task_id)
        if current is None:
            outside.append(task_id)
            continue

        completed = task.group("mark").lower() == "x"
        rest = task.group("rest").lstrip()
        parallel = rest.startswith("[P]")

        current["total"] += 1
        current["completed"] += int(completed)
        current["pending"] += int(not completed)
        current["parallel"] += int((not completed) and parallel)

    if not phases:
        raise RuntimeError("tasks.md has no '## Phase N: ...' headings")
    if phase_numbers != sorted(phase_numbers) or len(set(phase_numbers)) != len(phase_numbers):
        raise RuntimeError("task phases are duplicated or out of order")
    if duplicates:
        raise RuntimeError("duplicate task IDs: " + ", ".join(sorted(set(duplicates))))
    if outside:
        raise RuntimeError("tasks outside a phase: " + ", ".join(outside))

    total = sum(p["total"] for p in phases)
    if not total:
        raise RuntimeError("tasks.md has no executable task checklist items")

    pending_phases = [p for p in phases if p["pending"]]
    current_phase = pending_phases[0] if pending_phases else None
    if current_phase:
        later_started = [
            p["number"]
            for p in phases
            if p["number"] > current_phase["number"] and p["completed"]
        ]
        if later_started:
            raise RuntimeError(
                f"later phase(s) {later_started} already contain completed work "
                f"while phase {current_phase['number']} is still pending"
            )

    return {
        "phase_count": len(phases),
        "task_count": total,
        "pending": sum(p["pending"] for p in phases),
        "pending_parallel": sum(p["parallel"] for p in phases),
        "current_phase_number": current_phase["number"] if current_phase else 0,
        "current_phase_name": current_phase["name"] if current_phase else "",
        "current_phase_pending": current_phase["pending"] if current_phase else 0,
        "current_phase_parallel": current_phase["parallel"] if current_phase else 0,
    }


class Doctor:
    def __init__(self, project: Path | None, launcher_runtime: str, offline: bool, target: str):
        self.project = project
        self.launcher_runtime = launcher_runtime
        self.offline = offline
        self.target = target
        self.checks: list[dict[str, str]] = []

    def add(self, name: str, status: str, detail: str, remediation: str = "") -> None:
        self.checks.append(
            {"name": name, "status": status, "detail": detail, "remediation": remediation}
        )

    def fail(self, name: str, detail: str, remediation: str) -> None:
        self.add(name, "FAIL", detail, remediation)

    def run(self) -> dict[str, Any]:
        self._environment()
        if self.project is not None:
            self._project()
            self._powerpack()
            self._git()
            self._feature()
        self._review_prerequisites()
        counts = {key: sum(c["status"] == key for c in self.checks) for key in ("PASS", "WARN", "FAIL", "SKIP")}
        return {
            "schema": "powerpack-doctor/v1",
            "powerpack_version": POWERPACK_VERSION,
            "project_root": str(self.project) if self.project else "",
            "healthy": counts["FAIL"] == 0,
            "summary": counts,
            "checks": self.checks,
        }

    def _environment(self) -> None:
        specify = shutil.which("specify")
        if not specify:
            self.fail("specify-cli", "specify is not on PATH", "Install or activate Spec Kit >= 1.0.0.")
        else:
            rc, out, err = _run(specify, "--version")
            version = _semver(out + " " + err)
            if rc != 0 or version is None:
                self.fail("specify-cli", f"cannot determine Spec Kit version: {err or out}", "Repair the Specify CLI installation.")
            elif version < MIN_SPECKIT:
                self.fail("specify-version", f"Spec Kit {'.'.join(map(str, version))} is below 1.0.0", "Upgrade Spec Kit to >= 1.0.0.")
            else:
                self.add("specify-version", "PASS", f"Spec Kit {'.'.join(map(str, version))}")

        if self.project is None:
            self.fail("specify-project", "no .specify directory found from the current directory upward", "Run the doctor from an initialized Spec Kit project.")
        else:
            self.add("specify-project", "PASS", str(self.project))

    def _project(self) -> None:
        assert self.project is not None
        init_path = self.project / ".specify" / "init-options.json"
        if not init_path.is_file():
            self.fail("init-options", ".specify/init-options.json is missing", "Re-run Spec Kit initialization/upgrade.")
            return
        try:
            opts = _json(init_path)
        except Exception as exc:
            self.fail("init-options", f"invalid init-options.json: {exc}", "Repair or regenerate .specify/init-options.json.")
            return
        selected = str(opts.get("script") or "").strip()
        if selected not in {"sh", "ps", "py"}:
            self.fail("script-runtime", f"invalid selected runtime {selected!r}", "Select sh, ps, or py through Spec Kit initialization/integration setup.")
        elif self.launcher_runtime and selected != self.launcher_runtime:
            self.fail(
                "script-runtime",
                f"Spec Kit selected {selected!r}, but doctor was materialized as {self.launcher_runtime!r}",
                "Refresh/reinstall the PowerPack extension for the active integration so command scripts match init-options.json.",
            )
        else:
            self.add("script-runtime", "PASS", f"selected runtime: {selected}")

        integration_path = self.project / ".specify" / "integration.json"
        if not integration_path.is_file():
            self.fail("integration", ".specify/integration.json is missing", "Install/select a Spec Kit integration.")
        else:
            try:
                integration = str((_json(integration_path) or {}).get("integration") or "").strip()
            except Exception as exc:
                self.fail("integration", f"invalid integration.json: {exc}", "Repair the active Spec Kit integration.")
            else:
                if integration:
                    self.add("integration", "PASS", integration)
                else:
                    self.fail("integration", "active integration is empty", "Select an active Spec Kit integration.")

    def _powerpack(self) -> None:
        assert self.project is not None
        ext_dir = self.project / ".specify" / "extensions" / "powerpack"
        manifest = ext_dir / "extension.yml"
        if not manifest.is_file():
            self.fail("powerpack-extension", "installed powerpack extension is missing", "Install PowerPack extension as documented in docs/INSTALLATION_AND_USAGE.md.")
            return
        text = manifest.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'(?m)^\s*version:\s*["\']?([^"\'\s]+)', text)
        version = match.group(1) if match else ""
        if version != POWERPACK_VERSION:
            self.fail("powerpack-version", f"installed extension version is {version or 'unknown'}, expected {POWERPACK_VERSION}", "Refresh the PowerPack installation.")
        else:
            self.add("powerpack-version", "PASS", version)
        for command in ("speckit.powerpack.deliver", "speckit.powerpack.doctor"):
            if command not in text:
                self.fail("public-command-surface", f"{command} is not declared by installed extension", "Refresh the PowerPack extension.")
            else:
                self.add(f"command:{command}", "PASS", "declared")

        registry = self.project / ".specify" / "extensions" / ".registry"
        try:
            reg = _json(registry)
            item = (reg.get("extensions") or {}).get("powerpack") if isinstance(reg, dict) else None
        except Exception as exc:
            self.fail("extension-registry", f"cannot read extension registry: {exc}", "Reinstall the PowerPack extension.")
        else:
            if not isinstance(item, dict):
                self.fail("extension-registry", "powerpack is not registered", "Reinstall the PowerPack extension.")
            elif item.get("enabled", True) is not True:
                self.fail("extension-registry", "powerpack extension is disabled", "Run: specify extension enable powerpack")
            else:
                self.add("extension-registry", "PASS", "powerpack enabled")

        workflow = self.project / ".specify" / "workflows" / "powerpack-delivery" / "workflow.yml"
        wf_registry = self.project / ".specify" / "workflows" / "workflow-registry.json"
        try:
            wf_reg = _json(wf_registry)
            wf_item = (wf_reg.get("workflows") or {}).get("powerpack-delivery") if isinstance(wf_reg, dict) else None
        except Exception as exc:
            self.fail("workflow-registry", f"cannot read workflow registry: {exc}", "Reinstall the powerpack-delivery workflow.")
            wf_item = None
        if not workflow.is_file() or not isinstance(wf_item, dict):
            self.fail("delivery-workflow", "powerpack-delivery workflow is not completely installed", "Install the workflow as documented.")
        else:
            body = workflow.read_text(encoding="utf-8", errors="replace")
            required = (
                "id: checklist-convergence",
                "id: implementation-plan",
                "action: task-plan",
                "command: speckit.implement",
                "Mark a task [P] only",
                "id: review-convergence",
                "Every finding is mandatory",
                "active SPEC",
            )
            missing = [token for token in required if token not in body]
            if missing:
                self.fail("delivery-workflow", f"workflow is stale; missing contract markers: {missing}", "Refresh the installed PowerPack workflow.")
            else:
                workflow_version = str(wf_item.get("version") or "")
                if workflow_version != POWERPACK_VERSION:
                    self.fail(
                        "delivery-workflow",
                        f"installed workflow version is {workflow_version or 'unknown'}, expected {POWERPACK_VERSION}",
                        "Install the matching versioned PowerPack workflow release asset.",
                    )
                else:
                    self.add("delivery-workflow", "PASS", workflow_version)

        step_dir = self.project / ".specify" / "workflows" / "steps" / "powerpack-control"
        step_registry = self.project / ".specify" / "workflows" / "steps" / "step-registry.json"
        try:
            step_reg = _json(step_registry)
            step_item = (step_reg.get("steps") or {}).get("powerpack-control") if isinstance(step_reg, dict) else None
        except Exception as exc:
            self.fail("step-registry", f"cannot read step registry: {exc}", "Install powerpack-control from the PowerPack step catalog.")
            step_item = None
        required_step_files = ("step.yml", "__init__.py", "state.py", "review.py", "deep-review-protocol.md")
        missing_step = [name for name in required_step_files if not (step_dir / name).is_file()]
        if not isinstance(step_item, dict) or missing_step:
            self.fail("powerpack-control-step", f"custom step incomplete; missing={missing_step}", "Install/refresh powerpack-control from the PowerPack step catalog.")
        else:
            step_version = str(step_item.get("version") or "")
            if step_version != POWERPACK_VERSION:
                self.fail(
                    "powerpack-control-step",
                    f"installed step version is {step_version or 'unknown'}, expected {POWERPACK_VERSION}",
                    "Install the matching versioned powerpack-control step catalog entry.",
                )
            else:
                self.add("powerpack-control-step", "PASS", step_version)

    def _git(self) -> None:
        assert self.project is not None
        git = shutil.which("git")
        if not git:
            self.fail("git", "git is not on PATH", "Install Git.")
            return
        rc, remote, err = _run(git, "-C", str(self.project), "remote", "get-url", "origin")
        if rc != 0:
            self.fail("git-origin", err or "origin is missing", "Configure origin to the GitHub repository used by review.")
        elif "github.com" not in remote:
            self.fail("git-origin", f"origin is not github.com: {remote}", "PowerPack review currently requires a github.com origin.")
        else:
            self.add("git-origin", "PASS", remote)
        rc, status, _ = _run(git, "-C", str(self.project), "status", "--porcelain")
        if rc == 0 and status:
            self.add("git-working-tree", "WARN", "working tree has local changes; delivery can continue, but exact review requires committed/pushed HEAD")
        elif rc == 0:
            self.add("git-working-tree", "PASS", "clean")

    def _feature(self) -> None:
        assert self.project is not None
        feature, source = _feature_dir(self.project, self.target)
        marker_exists = (self.project / ".specify" / "feature.json").is_file() or bool(os.environ.get("SPECIFY_FEATURE_DIRECTORY"))
        if feature is None:
            if marker_exists or self.target:
                self.fail("active-feature", source, "Repair the active feature pointer/target so it resolves under specs/.")
            else:
                self.add("active-feature", "SKIP", source)
            return
        self.add("active-feature", "PASS", f"{feature.relative_to(self.project)} via {source}")
        for name in ("spec.md", "plan.md", "tasks.md"):
            path = feature / name
            self.add(
                f"feature:{name}",
                "PASS" if path.is_file() else "WARN",
                "present" if path.is_file() else "not created yet",
            )

        tasks_file = feature / "tasks.md"
        plan_file = feature / "plan.md"
        if tasks_file.is_file():
            if not plan_file.is_file():
                self.fail(
                    "implementation-task-plan",
                    "tasks.md exists without plan.md",
                    "Restore/generate plan.md before continuing implementation.",
                )
            else:
                try:
                    summary = _task_plan_summary(feature)
                except Exception as exc:
                    self.fail(
                        "implementation-task-plan",
                        str(exc),
                        "Repair tasks.md phase ordering/IDs before PowerPack delivery.",
                    )
                else:
                    phase = (
                        f"Phase {summary['current_phase_number']}: "
                        f"{summary['current_phase_name']}"
                        if summary["current_phase_number"]
                        else "all phases complete"
                    )
                    self.add(
                        "implementation-task-plan",
                        "PASS",
                        (
                            f"{summary['phase_count']} phases, "
                            f"{summary['task_count']} tasks, "
                            f"{summary['pending']} pending, "
                            f"{summary['pending_parallel']} pending [P]; "
                            f"current={phase}"
                        ),
                    )
        else:
            self.add(
                "implementation-task-plan",
                "SKIP",
                "tasks.md not created yet",
            )

        checklists = feature / "checklists"
        total = checked = 0
        if checklists.is_dir():
            for path in checklists.rglob("*.md"):
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if re.match(r"^\s*-\s*\[[ xX]\]\s+", line):
                        total += 1
                        checked += int(bool(re.match(r"^\s*-\s*\[[xX]\]\s+", line)))
        if total:
            status = "PASS" if checked == total else "WARN"
            self.add("feature-checklists", status, f"{checked}/{total} reviewer checklist items checked")
        else:
            self.add("feature-checklists", "SKIP", "no reviewer checklist items found")

        review = self.project / ".specify" / "powerpack" / "delivery" / "reviews" / "current.json"
        if review.is_file():
            try:
                payload = _json(review)
                verdict = str(payload.get("verdict") or "")
            except Exception as exc:
                self.fail("review-state", f"invalid current review JSON: {exc}", "Remove/repair only through a fresh PowerPack review; do not hand-edit review evidence.")
            else:
                self.add("review-state", "PASS", verdict or "review file present")
        else:
            self.add("review-state", "SKIP", "no PowerPack review has been produced yet")

    def _review_prerequisites(self) -> None:
        codex = shutil.which("codex")
        if not codex:
            self.fail("codex-cli", "codex is not on PATH", "Install/activate Codex CLI; independent review uses it as the read-only reviewer host.")
            return
        self.add("codex-cli", "PASS", codex)
        try:
            token, account = _codex_auth()
        except Exception as exc:
            self.fail("codex-auth", str(exc), "Run: codex login")
            return
        self.add("codex-auth", "PASS", "authenticated (credentials not displayed)")
        if self.offline:
            self.add("github-app", "SKIP", "network validation skipped by --offline")
            return
        try:
            installed = _request(token, account, "GET", "/ps/plugins/installed?limit=1000")
            plugins = installed.get("plugins") if isinstance(installed, dict) else []
            ids: list[str] = []
            for item in plugins if isinstance(plugins, list) else []:
                if not isinstance(item, dict):
                    continue
                release = item.get("release") if isinstance(item.get("release"), dict) else {}
                names = {
                    str(item.get("name") or "").casefold(),
                    str(item.get("display_name") or "").casefold(),
                    str(release.get("display_name") or "").casefold(),
                }
                if "github" not in names or str(item.get("status") or "").upper() != "ENABLED":
                    continue
                values = [item.get("connector_id"), item.get("canonical_app_id"), *(release.get("app_ids") or [])]
                found = [str(v) for v in values if isinstance(v, str) and v.startswith("connector_")]
                ids.extend(found)
            ids = list(dict.fromkeys(ids))
            if len(ids) != 1:
                raise RuntimeError(f"expected exactly one enabled GitHub connector, found {len(ids)}")
            availability = _request(
                token,
                account,
                "POST",
                "/apps/availability?platform=chat&locale=en-US",
                {"app_ids": [ids[0]]},
            )
            apps = availability.get("apps") if isinstance(availability, dict) else []
            app = next((x for x in apps if isinstance(x, dict) and x.get("id") == ids[0]), None)
            if not app or app.get("installed") is not True or app.get("available") is not True:
                raise RuntimeError("GitHub connector is not installed and available")
        except Exception as exc:
            self.fail("github-app", str(exc), "Enable one GitHub App/connector for the Codex account and verify repository access.")
        else:
            self.add("github-app", "PASS", "exactly one enabled and available GitHub connector")


def _render(report: dict[str, Any]) -> str:
    lines = [
        f"Specify PowerPack doctor v{report['powerpack_version']}",
        f"Project: {report['project_root'] or '<not found>'}",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"[{check['status']}] {check['name']}: {check['detail']}")
        if check["remediation"]:
            lines.append(f"       fix: {check['remediation']}")
    summary = report["summary"]
    lines += [
        "",
        f"Summary: PASS={summary['PASS']} WARN={summary['WARN']} FAIL={summary['FAIL']} SKIP={summary['SKIP']}",
        "HEALTHY" if report["healthy"] else "UNHEALTHY",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speckit.powerpack.doctor")
    parser.add_argument("target", nargs="?", default="", help="Optional active SPEC id/directory")
    parser.add_argument("--offline", action="store_true", help="Skip GitHub App connectivity validation")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--launcher-runtime", choices=("sh", "ps", "py"), default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    project = _find_project(Path.cwd())
    report = Doctor(project, args.launcher_runtime, args.offline, args.target).run()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_render(report))
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
