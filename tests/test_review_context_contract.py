from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from speckit_powerpack.review_context_contract import (
    ReviewContextError,
    _blocked_review_status,
    local_context_prompt,
    resolve_local_review_context,
    resolve_web_review_context,
    web_context_prompt,
)


def _git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=project,
        check=True,
        text=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, branch: str = "spec/soak-002-soak-runtime") -> Path:
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init")
    _git(project, "checkout", "-b", branch)
    _git(project, "remote", "add", "origin", "https://github.com/example/project.git")
    return project


def test_local_review_resolves_current_branch_to_current_spec(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    spec = project / "specs" / "soak-002-soak-runtime"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text("# Soak SPEC\n", encoding="utf-8")

    context = resolve_local_review_context(project)

    assert context.branch == "spec/soak-002-soak-runtime"
    assert context.spec_dir == spec
    prompt = local_context_prompt(project)
    assert "review_mode: local-spec-branch" in prompt
    assert "branch: spec/soak-002-soak-runtime" in prompt
    assert "spec: specs/soak-002-soak-runtime" in prompt
    assert "pull_request: NOT_REQUIRED" in prompt


def test_local_review_fails_closed_without_matching_spec(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    other = project / "specs" / "different-spec"
    other.mkdir(parents=True)
    (other / "spec.md").write_text("# Other\n", encoding="utf-8")

    with pytest.raises(ReviewContextError, match="Could not resolve exactly one Spec Kit SPEC"):
        resolve_local_review_context(project)


def test_web_review_requires_explicit_pr(tmp_path: Path) -> None:
    project = _repo(tmp_path)

    with pytest.raises(ReviewContextError, match="requires an explicit --pr"):
        resolve_web_review_context(project, None)


def test_web_review_normalizes_numeric_pr_for_current_origin(tmp_path: Path) -> None:
    project = _repo(tmp_path)

    context = resolve_web_review_context(project, "42")

    assert context.repository == "example/project"
    assert context.pull_request_number == 42
    assert context.pull_request_url == "https://github.com/example/project/pull/42"


def test_web_review_rejects_pr_from_another_repository(tmp_path: Path) -> None:
    project = _repo(tmp_path)

    with pytest.raises(ReviewContextError, match="does not match current origin"):
        resolve_web_review_context(project, "https://github.com/other/repo/pull/7")


def test_web_review_requires_github_plugin_permission_attestation(tmp_path: Path) -> None:
    project = _repo(tmp_path)

    with pytest.raises(ReviewContextError, match="ChatGPT/GitHub plugin"):
        web_context_prompt(project, "42", github_plugin_authorized=False)

    prompt = web_context_prompt(project, "42", github_plugin_authorized=True)
    assert "review_mode: web-pull-request" in prompt
    assert "pull_request_url: https://github.com/example/project/pull/42" in prompt
    assert "github_plugin_authorization: USER_CONFIRMED" in prompt
    assert "exactly this pull request" in prompt
    assert "BLOCKED_CAPABILITY" in prompt
    assert "BLOCKED_CONFIGURATION" in prompt


def test_web_prompt_distinguishes_missing_tool_from_missing_permission(tmp_path: Path) -> None:
    project = _repo(tmp_path)

    prompt = web_context_prompt(project, "42", github_plugin_authorized=True)

    assert "no GitHub plugin/connector/tool at all" in prompt
    assert "BLOCKED_CAPABILITY" in prompt
    assert "available but cannot access this exact repository or pull request" in prompt
    assert "BLOCKED_CONFIGURATION" in prompt


def test_blocked_review_status_detects_fail_closed_verdicts() -> None:
    assert _blocked_review_status("# BLOCKED_CAPABILITY\nNo GitHub tool") == "BLOCKED_CAPABILITY"
    assert _blocked_review_status("BLOCKED_CONFIGURATION\nPermission denied") == "BLOCKED_CONFIGURATION"
    assert _blocked_review_status("## BLOCKED_REVIEW_CONTEXT\nNo SPEC") == "BLOCKED_REVIEW_CONTEXT"
    assert _blocked_review_status("APPROVED\nNo findings") is None
