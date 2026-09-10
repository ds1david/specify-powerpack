"""SPEC-001 / T025-T051 gap reduction.

The full browserless `implement-review` flow can only be homologated end to end
with live Codex + a ChatGPT Project binding + a real PR. These tests close the
part of that gap that does NOT need live services: they prove the flow's **code
path** carries no reference to a command or runtime helper removed by SPEC-001,
and that the local plumbing (binding load, PR resolution, SPEC context,
`HEAD`) still runs after the cleanup — failing only at the live-service boundary
with a clean, typed error.
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from speckit_powerpack import browserless_review as br
from speckit_powerpack.browserless_review import BrowserlessReviewError

ROOT = Path(__file__).parents[1]
PKG = ROOT / "src" / "speckit_powerpack"
ASSETS = PKG / "assets"

# Tokens that must not appear anywhere the implement-review flow can reach.
REMOVED_TOKENS = (
    "powerpack_debt",
    "powerpack_full_cycle",
    "implement_runs",
    "latest_implement_files",
    "bin/debt.py",
    "bin/full_cycle.py",
    "speckit.implement.md",
    "speckit.converge.md",
    "speckit.checklist-converge",
    "speckit.full-cycle",
    "speckit.debt-",
)


def _powerpack_deps(entry: str) -> set[str]:
    seen: set[str] = set()
    stack = [entry]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        f = PKG / f"{mod}.py"
        if not f.is_file():
            continue
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level == 1:
                    stack.append(node.module)
                elif node.module.startswith("speckit_powerpack."):
                    stack.append(node.module.split(".", 1)[1])
    return seen


def test_implement_review_flow_carries_no_removed_command_reference():
    files = [PKG / f"{m}.py" for m in _powerpack_deps("browserless_review")]
    files += [
        ASSETS / "runtime" / "powerpack_runtime.py",
        ASSETS / "runtime" / "powerpack_capabilities.py",
        ASSETS / "runtime" / "powerpack_review_protocol.py",
        ASSETS / "presets" / "powerpack-core" / "commands" / "speckit.implement-review.md",
        ASSETS / "review" / "deep-review-protocol.md",
    ]
    offenders: list[str] = []
    for path in files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in REMOVED_TOKENS:
            for i, line in enumerate(text.splitlines(), 1):
                if token not in line:
                    continue
                # Allowed: prose that names a removed token to explain the removal
                # (only in the command doc / research-style comments).
                low = line.lower()
                if path.suffix == ".md" and any(
                    w in low for w in ("removed", "no longer", "upstream", "not a", "gone")
                ):
                    continue
                if "removed" in low or "replaced the removed" in low:
                    continue
                offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, "removed-command reference on the implement-review path:\n" + "\n".join(offenders)


def test_implement_review_flow_never_imports_removed_runtime_modules():
    reachable = _powerpack_deps("browserless_review") | _powerpack_deps("cli")
    assert "powerpack_debt" not in reachable
    assert "powerpack_full_cycle" not in reachable
    # the removed runtimes are not even present as files
    assert not (ASSETS / "runtime" / "powerpack_debt.py").exists()
    assert not (ASSETS / "runtime" / "powerpack_full_cycle.py").exists()


class _FakeBackendClient:
    """Stands in for `ChatGPTBackendClient`; fails exactly where the live
    service boundary is, so everything before it must have executed."""

    def __init__(self, *_a, **_k) -> None:
        pass

    def validate_auth(self) -> None:
        raise br.ChatGPTProjectError("no codex auth in test environment")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_browserless_review_local_plumbing_survives_cleanup(tmp_path: Path, monkeypatch):
    root = tmp_path / "proj"
    (root / ".specify" / "powerpack").mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.email", "t@e.com")
    _git(root, "config", "user.name", "T")
    _git(root, "remote", "add", "origin", "https://github.com/acme/widget.git")
    (root / ".specify" / "powerpack" / "review.json").write_text(
        '{"provider": "chatgpt-project", "chatgpt_project": '
        '{"project_id": "g-p-abc123", "project_name": "Widget", '
        '"authorization": "codex-backend-api"}}'
    )
    feature = root / "specs" / "001-demo"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Spec 001\nFR-001 do the thing.\n")
    (feature / "plan.md").write_text("# Plan\n")
    (root / "src.py").write_text("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    _git(root, "branch", "-M", "001-demo")

    monkeypatch.setattr(br, "ChatGPTBackendClient", _FakeBackendClient)

    with pytest.raises(BrowserlessReviewError) as excinfo:
        br.run_browserless_code_review(project_path=root, pull_request=7)

    # Reached the live-service boundary — not a missing module/attr/name from the cleanup.
    assert not isinstance(excinfo.value, (ImportError, AttributeError, NameError))
    assert "codex auth" in str(excinfo.value).lower()


def test_browserless_review_rejects_pr_repo_mismatch_before_any_network(tmp_path: Path):
    """`resolve_pull_request` (local, git-only) still guards the PR ↔ origin match."""
    root = tmp_path / "proj"
    (root / ".specify" / "powerpack").mkdir(parents=True)
    _git(root, "init")
    _git(root, "remote", "add", "origin", "https://github.com/acme/widget.git")
    with pytest.raises(BrowserlessReviewError):
        br.run_browserless_code_review(
            project_path=root, pull_request="https://github.com/other/repo/pull/1"
        )
