from __future__ import annotations

from pathlib import Path

import pytest

from speckit_powerpack.browserless_review import (
    BrowserlessReviewError,
    _review_prompt,
    _validate_hardened_review_contract,
    _validate_project_evidence,
    _validate_snapshot_contract,
    load_project_binding,
)
from speckit_powerpack.review_context import ReviewSnapshot


def _snapshot() -> ReviewSnapshot:
    return ReviewSnapshot(
        repository="owner/repo",
        pull_request_number=12,
        pull_request_url="https://github.com/owner/repo/pull/12",
        spec_id="SPEC-12",
        base_ref="main",
        base_sha="1" * 40,
        merge_base="2" * 40,
        head_sha="3" * 40,
        changed_files=("a.py", "b.py"),
        snapshot_sha256="4" * 64,
    )


def _hardened_review() -> dict:
    snapshot = _snapshot()
    return {
        "verdict": "APPROVED",
        "review_context": snapshot.review_context(),
        "coverage": {
            "changed_files": ["a.py", "b.py"],
            "requirements": [
                {"id": "FR-001", "status": "PASS", "evidence": ["proof"]},
                {"id": "SC-002", "status": "PASS", "evidence": ["proof"]},
            ],
            "inspection_evidence": [
                {"file": "a.py", "evidence": "inspected behavior and callers"},
                {"file": "b.py", "evidence": "inspected failure handling"},
            ],
            "verdict_challenge": {
                "strongest_counterexample": "retry can duplicate effect",
                "result": "SURVIVED",
                "evidence": ["idempotency guard is enforced"],
            },
            "context_gaps": [],
        },
    }


def test_load_binding_uses_schema5_chatgpt_project(tmp_path: Path):
    base = tmp_path / ".specify" / "powerpack"
    base.mkdir(parents=True)
    (base / "review.json").write_text(
        '{"provider":"chatgpt-project","chatgpt_project":{"project_id":"g-p-test","project_name":"Example","project_url":"https://chatgpt.com/g/x/project","authorization":"codex-backend-api"}}',
        encoding="utf-8",
    )
    binding = load_project_binding(tmp_path)
    assert binding.project_id == "g-p-test"
    assert binding.project_name == "Example"


def test_review_prompt_binds_project_spec_snapshot_and_github_app():
    prompt = _review_prompt(
        connector_id="connector_github",
        snapshot=_snapshot(),
        project_name="Example",
        project_context="CHATGPT PROJECT: Example\nmission: build safely",
        spec_context="FR-001 requirement\nSC-002 success criterion",
        protocol="schema 2.0 protocol",
        user_instruction="review it",
        previous_review="",
    )
    assert "[$github](app://connector_github)" in prompt
    assert '"snapshot_sha256": "' + "4" * 64 + '"' in prompt
    assert "CHATGPT PROJECT CONTEXT" in prompt
    assert "ACTIVE SPEC KIT CONTEXT" in prompt
    assert "schema 2.0 review JSON" in prompt
    assert '"FR-001"' in prompt
    assert '"SC-002"' in prompt
    assert "coverage.inspection_evidence" in prompt
    assert "coverage.verdict_challenge" in prompt
    assert "coverage.context_gaps" in prompt


def test_project_context_evidence_must_be_literal():
    review = {"project_context_evidence": {"project_name": "Example", "literal_evidence": "mission build safely"}}
    _validate_project_evidence(review, project_name="Example", project_context="prefix mission build safely suffix")
    review["project_context_evidence"]["literal_evidence"] = "invented evidence does not exist"
    with pytest.raises(BrowserlessReviewError, match="not a literal excerpt"):
        _validate_project_evidence(review, project_name="Example", project_context="prefix mission build safely suffix")


def test_snapshot_contract_requires_exact_changed_files():
    snapshot = _snapshot()
    review = {
        "review_context": snapshot.review_context(),
        "coverage": {"changed_files": ["a.py", "b.py"]},
    }
    _validate_snapshot_contract(review, snapshot)
    review["coverage"]["changed_files"] = ["a.py"]
    with pytest.raises(BrowserlessReviewError, match="changed-file list"):
        _validate_snapshot_contract(review, snapshot)


def test_hardened_contract_accepts_exact_requirements_evidence_challenge_and_no_gaps():
    _validate_hardened_review_contract(
        _hardened_review(),
        snapshot=_snapshot(),
        spec_context="FR-001 requirement\nSC-002 success criterion",
    )


def test_hardened_contract_rejects_missing_requirement_id():
    review = _hardened_review()
    review["coverage"]["requirements"] = review["coverage"]["requirements"][:1]
    with pytest.raises(BrowserlessReviewError, match="requirement IDs"):
        _validate_hardened_review_contract(
            review,
            snapshot=_snapshot(),
            spec_context="FR-001 requirement\nSC-002 success criterion",
        )


def test_hardened_contract_rejects_missing_changed_file_evidence():
    review = _hardened_review()
    review["coverage"]["inspection_evidence"] = review["coverage"]["inspection_evidence"][:1]
    with pytest.raises(BrowserlessReviewError, match="Every changed file requires inspection evidence"):
        _validate_hardened_review_contract(
            review,
            snapshot=_snapshot(),
            spec_context="FR-001 requirement\nSC-002 success criterion",
        )


def test_hardened_contract_blocks_approval_with_context_gap():
    review = _hardened_review()
    review["coverage"]["context_gaps"] = ["Project-only invariant is not durable yet"]
    with pytest.raises(BrowserlessReviewError, match="forbidden"):
        _validate_hardened_review_contract(
            review,
            snapshot=_snapshot(),
            spec_context="FR-001 requirement\nSC-002 success criterion",
        )
