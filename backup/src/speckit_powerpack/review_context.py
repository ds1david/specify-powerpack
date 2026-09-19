from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse


class ReviewContextError(RuntimeError):
    pass


@dataclass(frozen=True)
class PullRequestTarget:
    repository: str
    number: int
    url: str


@dataclass(frozen=True)
class SpecContext:
    spec_id: str
    spec_dir: Path
    branch: str
    serialized: str


@dataclass(frozen=True)
class ReviewSnapshot:
    repository: str
    pull_request_number: int
    pull_request_url: str
    spec_id: str
    base_ref: str
    base_sha: str
    merge_base: str
    head_sha: str
    changed_files: tuple[str, ...]
    snapshot_sha256: str

    def review_context(self) -> dict[str, str]:
        return {
            "spec_id": self.spec_id,
            "base_ref": self.base_ref,
            "base_sha": self.base_sha,
            "merge_base": self.merge_base,
            "head_sha": self.head_sha,
            "snapshot_sha256": self.snapshot_sha256,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "pull_request_number": self.pull_request_number,
            "pull_request_url": self.pull_request_url,
            **self.review_context(),
            "changed_files": list(self.changed_files),
        }


def git(project: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ReviewContextError((proc.stderr or proc.stdout or "git command failed").strip())
    return proc.stdout.strip()


def current_branch(project: Path) -> str:
    branch = git(project, "branch", "--show-current")
    if not branch:
        raise ReviewContextError("Review requires a named Git branch; detached HEAD is not supported.")
    return branch


def current_head(project: Path) -> str:
    head = git(project, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", head):
        raise ReviewContextError("Could not resolve a full local HEAD SHA.")
    return head.lower()


def github_repository(project: Path) -> str:
    remote = git(project, "remote", "get-url", "origin")
    match = re.fullmatch(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?", remote)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    parsed = urlparse(remote)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        raise ReviewContextError("Code review requires origin to point to github.com.")
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise ReviewContextError(f"Cannot derive owner/repository from origin: {remote}")
    return f"{parts[0]}/{parts[1]}"


def resolve_pull_request(project: Path, value: str | int | None) -> PullRequestTarget:
    if value is None or not str(value).strip():
        raise ReviewContextError("Browserless GitHub code review requires explicit --pr <number|GitHub PR URL>.")
    repository = github_repository(project)
    raw = str(value).strip()
    if raw.isdigit():
        number = int(raw)
        if number < 1:
            raise ReviewContextError("Pull request number must be greater than zero.")
        return PullRequestTarget(repository, number, f"https://github.com/{repository}/pull/{number}")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ReviewContextError("--pr must be a PR number or canonical github.com pull-request URL.")
    match = re.fullmatch(r"/([^/]+)/([^/]+)/pull/(\d+)/?", parsed.path)
    if not match:
        raise ReviewContextError("--pr URL must be https://github.com/<owner>/<repo>/pull/<number>.")
    url_repo = f"{match.group(1)}/{match.group(2)}"
    if url_repo.casefold() != repository.casefold():
        raise ReviewContextError(
            f"Pull request repository '{url_repo}' does not match current origin '{repository}'."
        )
    number = int(match.group(3))
    return PullRequestTarget(repository, number, f"https://github.com/{repository}/pull/{number}")


def _candidate_spec_names(branch: str) -> list[str]:
    values = [
        os.environ.get("SPECIFY_FEATURE", "").strip(),
        branch,
        branch.removeprefix("spec/"),
        branch.rsplit("/", 1)[-1],
    ]
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def resolve_spec_context(project: Path, *, max_chars: int = 48_000) -> SpecContext:
    branch = current_branch(project)
    specs_root = project / "specs"
    if not specs_root.is_dir():
        raise ReviewContextError(f"Spec Kit specs directory is missing: {specs_root}")
    matches: list[Path] = []
    for name in _candidate_spec_names(branch):
        candidate = specs_root / name
        if (candidate / "spec.md").is_file() and candidate not in matches:
            matches.append(candidate)
    if not matches:
        for candidate in specs_root.iterdir():
            if not candidate.is_dir() or not (candidate / "spec.md").is_file():
                continue
            leaf = branch.rsplit("/", 1)[-1]
            if branch.endswith(candidate.name) or candidate.name.endswith(leaf):
                matches.append(candidate)
    if len(matches) != 1:
        names = ", ".join(sorted(item.name for item in matches)) or "none"
        raise ReviewContextError(
            f"Could not resolve exactly one active SPEC for branch '{branch}'. Matches: {names}."
        )
    spec_dir = matches[0]
    sections: list[str] = []
    ordered_files = ["spec.md", "plan.md", "tasks.md", "research.md", "data-model.md", "quickstart.md"]
    for relative in ordered_files:
        path = spec_dir / relative
        if path.is_file():
            sections.append(f"### {relative}\n{path.read_text(encoding='utf-8', errors='replace')}")
    for directory in ("contracts", "checklists"):
        root = spec_dir / directory
        if root.is_dir():
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                rel = path.relative_to(spec_dir).as_posix()
                sections.append(f"### {rel}\n{path.read_text(encoding='utf-8', errors='replace')}")
    serialized = "\n\n".join(sections)[:max_chars]
    if not serialized.strip():
        raise ReviewContextError(f"Active SPEC contains no readable artifacts: {spec_dir}")
    return SpecContext(spec_dir.name, spec_dir, branch, serialized)


def _sha(value: object, *, field: str) -> str:
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        raise ReviewContextError(f"PR snapshot field '{field}' must be a full 40-character Git SHA.")
    return text


def build_snapshot(
    *,
    target: PullRequestTarget,
    spec_id: str,
    payload: dict[str, object],
    local_head: str,
) -> ReviewSnapshot:
    repository = str(payload.get("repository") or "").strip()
    number = int(payload.get("pull_request_number") or 0)
    if repository.casefold() != target.repository.casefold() or number != target.number:
        raise ReviewContextError("GitHub connector returned a different repository or pull request than requested.")
    base_ref = str(payload.get("base_ref") or "").strip()
    if not base_ref:
        raise ReviewContextError("PR snapshot did not include base_ref.")
    base_sha = _sha(payload.get("base_sha"), field="base_sha")
    merge_base = _sha(payload.get("merge_base"), field="merge_base")
    head_sha = _sha(payload.get("head_sha"), field="head_sha")
    if head_sha != local_head.lower():
        raise ReviewContextError(
            f"Local HEAD {local_head[:12]} does not match PR head {head_sha[:12]}; review would not bind to the local implementation snapshot."
        )
    raw_files = payload.get("changed_files")
    if not isinstance(raw_files, list):
        raise ReviewContextError("PR snapshot changed_files must be an array.")
    changed_files = tuple(sorted({str(item).strip() for item in raw_files if str(item).strip()}))
    if not changed_files:
        raise ReviewContextError("PR snapshot changed_files is empty.")
    canonical = {
        "repository": target.repository,
        "pull_request_number": target.number,
        "pull_request_url": target.url,
        "spec_id": spec_id,
        "base_ref": base_ref,
        "base_sha": base_sha,
        "merge_base": merge_base,
        "head_sha": head_sha,
        "changed_files": list(changed_files),
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return ReviewSnapshot(
        repository=target.repository,
        pull_request_number=target.number,
        pull_request_url=target.url,
        spec_id=spec_id,
        base_ref=base_ref,
        base_sha=base_sha,
        merge_base=merge_base,
        head_sha=head_sha,
        changed_files=changed_files,
        snapshot_sha256=digest,
    )
