from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

_TASK_RE = re.compile(
    r"^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<id>T\d{3,})\s+(?P<rest>.+?)\s*$"
)
_CHECK_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s+")
_PHASE_RE = re.compile(r"^##\s+Phase\s+(?P<number>\d+)\s*:\s*(?P<name>.+?)\s*$", re.IGNORECASE)
_PARALLEL_RE = re.compile(r"^\[P\](?:\s+|$)")
_STORY_RE = re.compile(r"^(?:\[P\]\s+)?\[(?P<story>US\d+)\](?:\s+|$)", re.IGNORECASE)


def git(project: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(project), *args],
        text=True,
        capture_output=True,
        check=False,
    )
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


def resolve_feature_dir(
    project: Path,
    target: str = "",
    *,
    require: bool = False,
) -> Path | None:
    project = project.resolve()
    feature = _safe_feature_path(
        project,
        os.environ.get("SPECIFY_FEATURE_DIRECTORY", ""),
    )
    if feature:
        return feature

    marker = project / ".specify" / "feature.json"
    if marker.is_file():
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        feature = _safe_feature_path(
            project,
            str(payload.get("feature_directory") or ""),
        )
        if feature:
            return feature

    normalized = target.strip().replace("\\", "/")
    if normalized.startswith("specs/"):
        normalized = normalized[6:].strip("/")
    feature = _safe_feature_path(
        project,
        f"specs/{normalized}" if normalized else "",
    )
    if feature:
        return feature

    specs = project / "specs"
    if normalized and specs.is_dir():
        candidates = [
            p.parent
            for p in specs.rglob("spec.md")
            if p.parent.name == normalized
        ]
        if len(candidates) == 1:
            return candidates[0].resolve()
        if len(candidates) > 1:
            raise RuntimeError(f"SPEC target {normalized!r} is ambiguous.")

    branch = git(project, "branch", "--show-current")
    if branch and specs.is_dir():
        leaf = branch.rsplit("/", 1)[-1]
        candidates = [
            p.parent
            for p in specs.rglob("spec.md")
            if p.parent.name == leaf
        ]
        if len(candidates) == 1:
            return candidates[0].resolve()

    if require:
        raise RuntimeError(
            "Could not resolve active SPEC. PowerPack follows Spec Kit authority: "
            "SPECIFY_FEATURE_DIRECTORY, .specify/feature.json, then "
            "unambiguous target/branch."
        )
    return None


def _parse_task_line(line: str) -> dict[str, Any] | None:
    match = _TASK_RE.match(line)
    if not match:
        return None
    rest = match.group("rest")
    parallel = bool(_PARALLEL_RE.match(rest))
    story_match = _STORY_RE.match(rest)
    story = story_match.group("story").upper() if story_match else ""
    return {
        "id": match.group("id"),
        "completed": match.group("mark").lower() == "x",
        "parallel": parallel,
        "story": story,
        "description": rest,
    }


def task_execution_plan(feature: Path) -> dict[str, Any]:
    plan = feature / "plan.md"
    tasks = feature / "tasks.md"
    if not plan.is_file():
        raise RuntimeError(f"plan.md not found for {feature}")
    if not tasks.is_file():
        raise RuntimeError(f"tasks.md not found for {feature}")

    phases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    tasks_outside_phase: list[str] = []
    phase_numbers: list[int] = []

    for lineno, line in enumerate(
        tasks.read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        phase_match = _PHASE_RE.match(line)
        if phase_match:
            number = int(phase_match.group("number"))
            current = {
                "number": number,
                "name": phase_match.group("name").strip(),
                "tasks": [],
            }
            phases.append(current)
            phase_numbers.append(number)
            continue

        task = _parse_task_line(line)
        if task is None:
            continue
        task["line"] = lineno
        if task["id"] in seen_ids:
            duplicate_ids.append(task["id"])
        seen_ids.add(task["id"])
        if current is None:
            tasks_outside_phase.append(task["id"])
            continue
        current["tasks"].append(task)

    if not phases:
        raise RuntimeError(
            "tasks.md contains no '## Phase N: ...' headings; "
            "phase-by-phase execution cannot be proven."
        )
    if phase_numbers != sorted(phase_numbers) or len(set(phase_numbers)) != len(phase_numbers):
        raise RuntimeError(
            "tasks.md phase numbers are duplicated or out of order."
        )
    if duplicate_ids:
        raise RuntimeError(
            "tasks.md contains duplicate task IDs: "
            + ", ".join(sorted(set(duplicate_ids)))
        )
    if tasks_outside_phase:
        raise RuntimeError(
            "tasks.md contains tasks outside a Phase heading: "
            + ", ".join(tasks_outside_phase)
        )

    all_tasks = [task for phase in phases for task in phase["tasks"]]
    if not all_tasks:
        raise RuntimeError("tasks.md contains no executable task checklist items.")

    for phase in phases:
        phase_tasks = phase["tasks"]
        phase["total"] = len(phase_tasks)
        phase["completed"] = sum(task["completed"] for task in phase_tasks)
        phase["pending"] = sum(not task["completed"] for task in phase_tasks)
        phase["pending_parallel"] = sum(
            (not task["completed"]) and task["parallel"]
            for task in phase_tasks
        )
        phase["pending_sequential"] = (
            phase["pending"] - phase["pending_parallel"]
        )

    pending_phases = [phase for phase in phases if phase["pending"]]
    current_phase = pending_phases[0] if pending_phases else None
    completed_phase_numbers = [
        phase["number"] for phase in phases if phase["pending"] == 0
    ]

    if current_phase is not None:
        later_started = [
            phase["number"]
            for phase in phases
            if phase["number"] > current_phase["number"]
            and phase["completed"] > 0
        ]
        if later_started:
            raise RuntimeError(
                "tasks.md shows completed work in later phase(s) "
                f"{later_started} while phase {current_phase['number']} "
                "still has pending tasks. Phase ordering is inconsistent."
            )

    return {
        "spec_id": feature.name,
        "plan_file": str(plan),
        "tasks_file": str(tasks),
        "phase_count": len(phases),
        "task_count": len(all_tasks),
        "completed_tasks": sum(task["completed"] for task in all_tasks),
        "pending_tasks": sum(not task["completed"] for task in all_tasks),
        "pending_parallel_tasks": sum(
            (not task["completed"]) and task["parallel"]
            for task in all_tasks
        ),
        "pending_sequential_tasks": sum(
            (not task["completed"]) and (not task["parallel"])
            for task in all_tasks
        ),
        "current_phase_number": (
            current_phase["number"] if current_phase else 0
        ),
        "current_phase_name": current_phase["name"] if current_phase else "",
        "current_phase_pending": current_phase["pending"] if current_phase else 0,
        "current_phase_parallel": (
            current_phase["pending_parallel"] if current_phase else 0
        ),
        "completed_phase_numbers": completed_phase_numbers,
        "phases": phases,
    }


def task_counts(tasks: Path) -> tuple[int, int]:
    total = pending = 0
    if not tasks.is_file():
        return total, pending
    for line in tasks.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        task = _parse_task_line(line)
        if task is None:
            continue
        total += 1
        if not task["completed"]:
            pending += 1
    return total, pending


def checklist_status(feature: Path) -> dict[str, Any]:
    root = feature / "checklists"
    files: list[dict[str, Any]] = []
    total = checked = unchecked = 0
    if root.is_dir():
        for path in sorted(root.rglob("*.md")):
            ft = fc = fu = 0
            for line in path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                match = _CHECK_RE.match(line)
                if not match:
                    continue
                ft += 1
                if match.group("mark").lower() == "x":
                    fc += 1
                else:
                    fu += 1
            if ft:
                files.append(
                    {
                        "path": path.relative_to(feature).as_posix(),
                        "total": ft,
                        "checked": fc,
                        "unchecked": fu,
                    }
                )
                total += ft
                checked += fc
                unchecked += fu
    return {
        "total": total,
        "checked": checked,
        "unchecked": unchecked,
        "files": files,
    }


def fingerprint_tasks(feature: Path) -> str:
    tasks = feature / "tasks.md"
    if not tasks.is_file():
        raise RuntimeError(f"tasks.md not found for {feature}")
    return hashlib.sha256(tasks.read_bytes()).hexdigest()


def review_state(project: Path, head: str) -> tuple[bool, str]:
    current = (
        project
        / ".specify"
        / "powerpack"
        / "delivery"
        / "reviews"
        / "current.json"
    )
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
    fresh = (
        str(context.get("head_sha") or "").strip().lower()
        == head.lower()
    )
    return (
        fresh and verdict in {"APPROVED", "CHANGES_REQUIRED", "BLOCKED"},
        verdict,
    )


def inspect_delivery(project: Path, target: str = "") -> dict[str, Any]:
    project = project.resolve()
    head = git(project, "rev-parse", "HEAD")
    branch = git(project, "branch", "--show-current")
    feature = resolve_feature_dir(project, target, require=False)

    if feature is None:
        return {
            "state": "NEW",
            "spec_id": "",
            "feature_dir": "",
            "branch": branch,
            "head_sha": head,
            "has_spec": False,
            "has_plan": False,
            "has_tasks": False,
            "task_count": 0,
            "pending_tasks": 0,
            "review_fresh": False,
            "review_verdict": "",
        }

    has_spec = (feature / "spec.md").is_file()
    has_plan = (feature / "plan.md").is_file()
    has_tasks = (feature / "tasks.md").is_file()
    if not has_spec:
        raise RuntimeError(f"Resolved feature {feature} has no spec.md.")
    if has_tasks and not has_plan:
        raise RuntimeError(
            "tasks.md exists without plan.md; mid-flight adoption is unsafe."
        )

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
        "state": state,
        "spec_id": feature.name,
        "feature_dir": str(feature),
        "branch": branch,
        "head_sha": head,
        "has_spec": has_spec,
        "has_plan": has_plan,
        "has_tasks": has_tasks,
        "task_count": task_count,
        "pending_tasks": pending,
        "review_fresh": fresh,
        "review_verdict": verdict if fresh else "",
    }
