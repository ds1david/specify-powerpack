from __future__ import annotations

from pathlib import Path

import pytest

from speckit_powerpack.review_context import (
    PullRequestTarget,
    ReviewContextError,
    build_snapshot,
    resolve_pull_request,
)


def test_resolve_pull_request_requires_exact_origin_repository(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("speckit_powerpack.review_context.github_repository", lambda project: "owner/repo")
    target = resolve_pull_request(tmp_path, "https://github.com/owner/repo/pull/92")
    assert target.repository == "owner/repo"
    assert target.number == 92
    with pytest.raises(ReviewContextError):
        resolve_pull_request(tmp_path, "https://github.com/other/repo/pull/92")


def test_snapshot_is_deterministic_and_requires_local_head_match():
    target = PullRequestTarget("owner/repo", 92, "https://github.com/owner/repo/pull/92")
    payload = {
        "repository": "owner/repo",
        "pull_request_number": 92,
        "base_ref": "main",
        "base_sha": "1" * 40,
        "merge_base": "2" * 40,
        "head_sha": "3" * 40,
        "changed_files": ["b.py", "a.py", "a.py"],
    }
    first = build_snapshot(target=target, spec_id="SPEC-1", payload=payload, local_head="3" * 40)
    second = build_snapshot(target=target, spec_id="SPEC-1", payload=payload, local_head="3" * 40)
    assert first.snapshot_sha256 == second.snapshot_sha256
    assert first.changed_files == ("a.py", "b.py")
    assert len(first.snapshot_sha256) == 64
    with pytest.raises(ReviewContextError, match="does not match PR head"):
        build_snapshot(target=target, spec_id="SPEC-1", payload=payload, local_head="4" * 40)
