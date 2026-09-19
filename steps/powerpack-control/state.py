from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

_TASK_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<id>T\d{3,})\b")
_CHECK_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s+")

def git(project: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(project), *args], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "git command failed").strip())
    return proc.stdout.strip()

def _safe_feature_path(project: Path, raw: str) -> Path | None:
    value = raw.strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = project / path
    try:
        resolved = path.resolve()
        resolved.relative_to((project / "specs").resolve())
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_dir() else None

def resolve_feature_dir(project: Path, target: str = "", *, require: bool = False) -> Path | None:
    project = project.resolve()
    feature = _safe_feature_path(project, os.environ.get("SPECIFY_FEATURE_DIRECTORY", ""))
    if feature:
        return feature

    marker = project / ".specify" / "feature.json"
    if marker.is_file():
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        feature = _safe_feature_path(project, str(payload.get("feature_directory") or ""))
        if feature:
            return feature

    normalized = target.strip().replace("\\", "/")
    if normalized.startswith("specs/"):
        normalized = normalized[6:].strip("/")
    feature = _safe_feature_path(project, f"specs/{normalized}" if normalized else "")
    if feature:
        return feature

    specs = project / "specs"
    if normalized and specs.is_dir():
        candidates = [p.parent for p in specs.rglob("spec.md") if p.parent.name == normalized]
        if len(candidates) == 1:
            return candidates[0].resolve()
        if len(candidates) > 1:
            raise RuntimeError(f"SPEC target {normalized!r} is ambiguous.")

    branch = git(project, "branch", "--show-current")
    if branch and specs.is_dir():
        leaf = branch.rsplit("/", 1)[-1]
        candidates = [p.parent for p in specs.rglob("spec.md") if p.parent.name == leaf]
        if len(candidates) == 1:
            return candidates[0].resolve()

    if require:
        raise RuntimeError(
            "Could not resolve active SPEC. PowerPack follows Spec Kit authority: "
            "SPECIFY_FEATURE_DIRECTORY, .specify/feature.json, then unambiguous target/branch."
        )
    return None

def task_counts(tasks: Path) -> tuple[int, int]:
    total = pending = 0
    if not tasks.is_file():
        return total, pending
    for line in tasks.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _TASK_RE.match(line)
        if not match:
            continue
        total += 1
        if match.group("mark") == " ":
            pending += 1
    return total, pending

def checklist_status(feature: Path) -> dict[str, Any]:
    root = feature / "checklists"
    files: list[dict[str, Any]] = []
    total = checked = unchecked = 0
    if root.is_dir():
        for path in sorted(root.rglob("*.md")):
            ft = fc = fu = 0
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                match = _CHECK_RE.match(line)
                if not match:
                    continue
                ft += 1
                if match.group("mark").lower() == "x":
                    fc += 1
                else:
                    fu += 1
            if ft:
                files.append({"path": path.relative_to(feature).as_posix(), "total": ft, "checked": fc, "unchecked": fu})
                total += ft
                checked += fc
                unchecked += fu
    return {"total": total, "checked": checked, "unchecked": unchecked, "files": files}

def fingerprint_tasks(feature: Path) -> str:
    tasks = feature / "tasks.md"
    if not tasks.is_file():
        raise RuntimeError(f"tasks.md not found for {feature}")
    return hashlib.sha256(tasks.read_bytes()).hexdigest()

def review_state(project: Path, head: str) -> tuple[bool, str]:
    current = project / ".specify" / "powerpack" / "delivery" / "reviews" / "current.json"
    if not current.is_file():
        return False, ""
    try:
        payload = json.loads(current.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ""
    context = payload.get("review_context") if isinstance(payload, dict) else None
    if not isinstance(context, dict):
        return False, ""
    verdict = str(payload.get("verdict") or "").strip().upper()
    fresh = str(context.get("head_sha") or "").strip().lower() == head.lower()
    return fresh and verdict in {"APPROVED", "CHANGES_REQUIRED", "BLOCKED"}, verdict

def inspect_delivery(project: Path, target: str = "") -> dict[str, Any]:
    project = project.resolve()
    head = git(project, "rev-parse", "HEAD")
    branch = git(project, "branch", "--show-current")
    feature = resolve_feature_dir(project, target, require=False)

    if feature is None:
        return {
            "state": "NEW", "spec_id": "", "feature_dir": "", "branch": branch, "head_sha": head,
            "has_spec": False, "has_plan": False, "has_tasks": False,
            "task_count": 0, "pending_tasks": 0, "review_fresh": False, "review_verdict": "",
        }

    has_spec = (feature / "spec.md").is_file()
    has_plan = (feature / "plan.md").is_file()
    has_tasks = (feature / "tasks.md").is_file()
    if not has_spec:
        raise RuntimeError(f"Resolved feature {feature} has no spec.md.")
    if has_tasks and not has_plan:
        raise RuntimeError("tasks.md exists without plan.md; mid-flight adoption is unsafe.")

    task_count, pending = task_counts(feature / "tasks.md")
    fresh, verdict = review_state(project, head)

    if not has_plan:
        state = "SPECIFIED"
    elif not has_tasks:
        state = "PLANNED"
    elif fresh and verdict == "APPROVED":
        state = "DELIVERED"
    elif fresh and verdict == "CHANGES_REQUIRED":
        state = "REVIEW_CHANGES_REQUIRED"
    elif pending:
        state = "IMPLEMENTATION_PENDING"
    else:
        state = "IMPLEMENTED_PENDING_CONVERGENCE"

    return {
        "state": state, "spec_id": feature.name, "feature_dir": str(feature), "branch": branch, "head_sha": head,
        "has_spec": has_spec, "has_plan": has_plan, "has_tasks": has_tasks,
        "task_count": task_count, "pending_tasks": pending,
        "review_fresh": fresh, "review_verdict": verdict if fresh else "",
    }
