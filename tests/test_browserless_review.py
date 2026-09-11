from __future__ import annotations

from pathlib import Path

import pytest

from speckit_powerpack.browserless_review import (
    BrowserlessReviewError,
    _review_prompt,
    _master_review_prompt,
    _review_packet,
    _snapshot_prompt,
    _validate_hardened_review_contract,
    _validate_project_evidence,
    _validate_snapshot_contract,
    load_project_binding,
    ProjectBinding,
)
from speckit_powerpack.chatgpt_pow_probe import build_conversation_body, parse_sse_assistant
from speckit_powerpack.review_context import PullRequestTarget
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
        "review_divergences": [],
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


def test_every_turn_carries_project_context_and_the_github_connector():
    """Firm requirement: BOTH the ChatGPT Project context and the GitHub App
    mention are in every prompt sent to ChatGPT — including the complete
    Master Review turn."""
    target = PullRequestTarget("owner/repo", 15, "https://github.com/owner/repo/pull/15")
    snap = _snapshot_prompt(target, "connector_github", project_context="CHATGPT PROJECT: Example\nmission: X")
    assert "plugin:connector_github" in snap
    assert "CHATGPT PROJECT CONTEXT" in snap and "mission: X" in snap
    # and it degrades cleanly when the Project has no readable context
    bare = _snapshot_prompt(target, "connector_github")
    assert "plugin:connector_github" in bare
    assert "NONE — the bound ChatGPT Project has no readable context" in bare


def test_web_transport_payload_keeps_project_and_dynamic_connector_binding():
    body = build_conversation_body(
        "list the changed files",
        "gpt-5-6-thinking",
        project_id="g-p-dynamic-project",
        github_repos=["owner/repo"],
        connector_id="connector_dynamic",
    )
    assert body["conversation_mode"] == {
        "kind": "gizmo_interaction",
        "gizmo_id": "g-p-dynamic-project",
    }
    assert body["system_hints"] == ["plugin:connector_dynamic"]
    metadata = body["messages"][0]["metadata"]
    assert metadata["system_hints"] == ["plugin:connector_dynamic"]
    assert metadata["selected_github_repos"] == ["owner/repo"]
    assert metadata["serialization_metadata"]["custom_symbol_offsets"][0]["id"] == "plugin:connector_dynamic"


def test_web_transport_parser_exposes_connector_tool_evidence():
    class Response:
        def iter_lines(self):
            yield b'data: {"type":"server_ste_metadata","metadata":{"tool_invoked":true,"tool_name":"ApiToolWrapper"}}'
            yield b'data: {"conversation_id":"conv-1"}'
            yield b'data: {"message":{"id":"assistant-1","author":{"role":"assistant"},"content":{"parts":["done"]}}}'
            yield b'data: [DONE]'

    text, meta = parse_sse_assistant(Response())
    assert text == "done"
    assert meta["conversation_id"] == "conv-1"
    assert meta["tool_invocations"] == ("ApiToolWrapper",)


def test_web_transport_parser_keeps_final_json_code_but_not_tool_code():
    class Response:
        def iter_lines(self):
            yield b'data: {"v":{"message":{"id":"tool-call","author":{"role":"assistant"},"recipient":"api_tool.call_tool","content":{"content_type":"code","text":"{\\"path\\":\\"/GitHub/get_pr_info\\"}"}}}}'
            yield b'data: {"v":{"message":{"id":"final","author":{"role":"assistant"},"recipient":"all","content":{"content_type":"code","text":"{\\"repository\\":\\"owner/repo\\"}"}}}}'
            yield b'data: [DONE]'

    text, _ = parse_sse_assistant(Response())
    assert text == '{"repository":"owner/repo"}'


def test_web_transport_parser_requests_allow_only_for_explicit_confirmation():
    class Response:
        def __init__(self, confirmation: bool):
            self.confirmation = confirmation

        def iter_lines(self):
            yield b'data: {"v":{"message":{"id":"assistant-1","author":{"role":"assistant"},"content":{"content_type":"code","text":"github call"}}}}'
            if self.confirmation:
                yield b'data: {"v":{"message":{"id":"tool-1","author":{"role":"tool","name":"api_tool.call_tool"},"content":{"content_type":"text","parts":[""]},"metadata":{"jit_plugin_data":{"from_server":{"type":"confirm_action","actions":[{"type":"allow","target_message_id":"assistant-1"}]}}}}}}'
            else:
                yield b'data: {"v":{"message":{"id":"tool-1","author":{"role":"tool","name":"api_tool.call_tool"},"content":{"content_type":"text","parts":["github result"]},"metadata":{}}}}'
            yield b'data: [DONE]'

    _, needs_allow = parse_sse_assistant(Response(True))
    _, already_allowed = parse_sse_assistant(Response(False))
    assert needs_allow["pending_allow"] == {
        "target_message_id": "assistant-1",
        "parent_message_id": "tool-1",
    }
    assert already_allowed["pending_allow"] == {}
    assert needs_allow["authorization_required"] is True
    assert already_allowed["authorization_required"] is False
    assert needs_allow["parent_message_id"] == "assistant-1"
    assert already_allowed["parent_message_id"] == "assistant-1"


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
    assert "plugin:connector_github" in prompt
    assert '"snapshot_sha256": "' + "4" * 64 + '"' in prompt
    assert "CHATGPT PROJECT CONTEXT" in prompt
    assert "ACTIVE SPEC KIT CONTEXT" in prompt
    assert "schema 2.0 review JSON" in prompt
    assert '"FR-001"' in prompt
    assert '"SC-002"' in prompt
    assert "coverage.inspection_evidence" in prompt
    assert "coverage.verdict_challenge" in prompt
    assert "coverage.context_gaps" in prompt


def test_master_review_packet_is_distinct_from_homologation_prompts():
    snapshot = _snapshot()
    packet = _review_packet(
        target=PullRequestTarget("owner/repo", 12, "https://github.com/owner/repo/pull/12"),
        spec=type("Spec", (), {"spec_id": "SPEC-12"})(),
        snapshot=snapshot,
        project=ProjectBinding("g-p-test", "Example", None),
        project_context="mission: build safely",
        protocol="protocol-v3",
        previous_review=None,
        round_number=1,
        attempt=1,
        segment=1,
        master_prompt="MASTER CONTRACT",
    )
    prompt = _master_review_prompt("MASTER CONTRACT", packet, target=PullRequestTarget("owner/repo", 12, "https://github.com/owner/repo/pull/12"))
    assert "MASTER CONTRACT" in prompt
    assert "POWERPACK_REVIEW_PACKET" in prompt
    assert packet["review_id"] == "owner/repo#12:SPEC-12:implement-review"
    assert packet["master_prompt"]["sha256"]
    assert "not a homologation probe" in prompt
    assert "Name the bound Project and summarize its mission" not in prompt


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
