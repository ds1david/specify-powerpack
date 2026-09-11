from __future__ import annotations

import json
from pathlib import Path

import pytest

from speckit_powerpack.browserless_review import (
    BrowserlessReviewError,
    _review_prompt,
    _master_review_prompt,
    _review_packet,
    _extract_json,
    _changed_files_for_snapshot,
    _missing_snapshot_fields,
    _retain_snapshot_repair_evidence,
    _complete_snapshot_from_local_git,
    _missing_inspection_files,
    _canonical_requirement_id,
    _merge_requirement_repair,
    _write_review_bundle,
    _external_blocked_reasons,
    _requirement_ids,
    _snapshot_prompt,
    _validate_hardened_review_contract,
    _validate_snapshot_contract,
    load_project_binding,
    ProjectBinding,
)
from speckit_powerpack.chatgpt_pow_probe import (
    build_conversation_body,
    human_wait,
    upload_prompt_attachments,
    parse_sse_assistant,
    send_connector_allow,
)
from speckit_powerpack.review_context import PullRequestTarget
from speckit_powerpack.review_context import ReviewSnapshot
from speckit_powerpack.review_response_normalizer import normalize_review_response


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


def test_normalizer_binds_immutable_snapshot_and_converts_shape_only():
    snapshot = _snapshot()
    review = {
        "verdict": "CHANGES_REQUIRED",
        "review_context": {"head_sha": "wrong"},
        "changed_files": {"files": ["wrong.py"]},
        "requirements": {"FR-001": {"status": "PASS", "evidence": ["proof"]}},
        "coverage": {
            "inspection_evidence": {
                "a.py": "inspected code path",
                "b.py": {"evidence": "inspected callers"},
            }
        },
    }

    normalized = normalize_review_response(review, snapshot)

    assert normalized["review_context"] == snapshot.review_context()
    assert normalized["coverage"]["changed_files"] == ["a.py", "b.py"]
    assert normalized["coverage"]["requirements"] == [
        {"id": "FR-001", "status": "PASS", "evidence": ["proof"]}
    ]
    assert normalized["coverage"]["inspection_evidence"] == [
        {"file": "a.py", "evidence": "inspected code path"},
        {"file": "b.py", "evidence": "inspected callers"},
    ]
    assert normalized["verdict"] == "CHANGES_REQUIRED"


def test_extract_json_allows_only_explicit_partial_repair_objects():
    partial = '{"coverage":{"inspection_evidence":[{"file":"a.py","evidence":"inspected"}]}}'

    with pytest.raises(BrowserlessReviewError):
        _extract_json(partial)

    assert _extract_json(partial, allow_partial=True)["coverage"]["inspection_evidence"]


def test_every_turn_uses_project_binding_and_the_github_connector():
    """The Web Project supplies context; the prompt only binds the connector."""
    target = PullRequestTarget("owner/repo", 15, "https://github.com/owner/repo/pull/15")
    snap = _snapshot_prompt(target, "connector_github")
    assert "plugin:connector_github" in snap
    assert "CHATGPT PROJECT CONTEXT" not in snap


def test_master_prompt_requires_github_connector_before_review_evidence():
    prompt = Path("src/speckit_powerpack/assets/review/master-review-prompt.md").read_text(encoding="utf-8")

    assert "Before reading or judging repository content, invoke the selected @GitHub" in prompt
    assert "Use ONLY the selected @GitHub connector" in prompt
    assert "ONE-MESSAGE EXECUTION MODEL" in prompt
    assert "Do not request a bootstrap" in prompt


def test_master_prompt_source_and_installed_copy_are_identical():
    source = Path("src/speckit_powerpack/assets/review/master-review-prompt.md").read_text(encoding="utf-8")
    installed = Path(".specify/powerpack/master-review-prompt.md").read_text(encoding="utf-8")

    assert installed == source


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


def test_web_transport_payload_carries_structured_review_attachments():
    body = build_conversation_body(
        "Execute review.",
        "gpt-5-6-thinking",
        project_id="g-p-dynamic-project",
        github_repos=["owner/repo"],
        connector_id="connector_dynamic",
        attachments=[{"name": "protocol.md", "mime_type": "text/markdown", "content": "RULES"}],
    )
    attachments = body["messages"][0]["metadata"]["powerpack_review_attachments"]
    assert attachments[0]["name"] == "protocol.md"
    assert attachments[0]["content"] == "RULES"
    assert attachments[0]["bytes"] == 5
    assert len(attachments[0]["sha256"]) == 64


def test_upload_prompt_attachment_follows_file_picker_sequence(monkeypatch):
    class Response:
        status_code = 200
        text = ""

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append(("POST", url, kwargs))
            if url.endswith("/files"):
                return Response({"file_id": "file_test", "upload_url": "https://upload.test/file"})
            return Response({})

        def put(self, url, **kwargs):
            self.calls.append(("PUT", url, kwargs))
            return Response({})

    waits = []
    monkeypatch.setattr("speckit_powerpack.chatgpt_pow_probe.human_wait", lambda: waits.append(True))
    session = Session()
    uploaded = upload_prompt_attachments(
        session,
        [{"name": "protocol.md", "mime_type": "text/markdown", "content": "RULES"}],
        project_id="g-p-test",
        conversation_id="conversation-test",
        origination_message_id="message-test",
    )
    assert uploaded == [{"id": "file_test", "size": 5, "name": "protocol.md", "mime_type": "text/markdown"}]
    assert [call[0] for call in session.calls] == ["POST", "PUT", "POST"]
    assert len(waits) == 3


def test_multiple_uploads_use_ace_upload_and_finish_before_return(monkeypatch):
    class Response:
        status_code = 200
        text = ""

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append(("POST", url, kwargs))
            if url.endswith("/files"):
                number = len([call for call in self.calls if call[1].endswith("/files")])
                return Response({"file_id": f"file_{number}", "upload_url": f"https://upload.test/{number}"})
            return Response({})

        def put(self, url, **kwargs):
            self.calls.append(("PUT", url, kwargs))
            return Response({})

    monkeypatch.setattr("speckit_powerpack.chatgpt_pow_probe.human_wait", lambda: None)
    session = Session()
    attachments = [
        {"name": "a.md", "mime_type": "text/markdown", "content": "A"},
        {"name": "b.json", "mime_type": "application/json", "content": "{}"},
    ]
    uploaded = upload_prompt_attachments(
        session, attachments, project_id="g-p-test", conversation_id="c-test", origination_message_id="m-test"
    )
    file_calls = [call for call in session.calls if call[1].endswith("/files")]
    process_calls = [call for call in session.calls if call[1].endswith("process_upload_stream")]
    assert len(uploaded) == 2
    assert all(call[2]["json"]["use_case"] == "ace_upload" for call in file_calls)
    assert len(process_calls) == 2
    assert all(call[2]["json"]["use_case"] == "ace_upload" for call in process_calls)
    assert session.calls[-1][1].endswith("process_upload_stream")


def test_web_transport_rejects_missing_connector_for_github():
    with pytest.raises(ValueError, match="current ChatGPT account"):
        build_conversation_body(
            "list the changed files",
            "gpt-5-6-thinking",
            project_id="g-p-dynamic-project",
            github_repos=["owner/repo"],
        )


def test_human_wait_uses_dynamic_interval(monkeypatch):
    observed = []
    monkeypatch.setattr("speckit_powerpack.chatgpt_pow_probe.random.uniform", lambda minimum, maximum: (minimum + maximum) / 2)
    monkeypatch.setattr("speckit_powerpack.chatgpt_pow_probe.time.sleep", observed.append)
    assert human_wait() == 2.75
    assert observed == [2.75]


def test_missing_snapshot_fields_requires_full_sha_values():
    assert _missing_snapshot_fields({"review_context": {"base_ref": "main"}}) == [
        "base_sha",
        "merge_base",
        "head_sha",
    ]
    assert _missing_snapshot_fields(
        {
            "review_context": {
                "base_ref": "main",
                "base_sha": "1" * 40,
                "merge_base": "2" * 40,
                "head_sha": "3" * 40,
            }
        }
    ) == []


def test_snapshot_repair_retains_non_empty_inspection_evidence():
    previous = {"coverage": {"inspection_evidence": [{"file": "a.py"}]}}
    repaired = {"review_context": {"merge_base": "2" * 40}, "coverage": {}}
    assert _retain_snapshot_repair_evidence(previous, repaired)["coverage"]["inspection_evidence"] == [
        {"file": "a.py"}
    ]


def test_local_git_snapshot_completion_only_fills_manifest_fields(tmp_path, monkeypatch):
    def fake_git(_root, *args):
        if args == ("symbolic-ref", "--short", "refs/remotes/origin/HEAD"):
            return "origin/main"
        if args == ("rev-parse", "origin/main"):
            return "1" * 40
        if args == ("merge-base", "1" * 40, "3" * 40):
            return "2" * 40
        if args == ("diff", "--name-only", "2" * 40 + ".." + "3" * 40):
            return "src/app.py"
        raise AssertionError(args)

    monkeypatch.setattr("speckit_powerpack.browserless_review.git", fake_git)
    review = {"findings": [{"id": "F1"}], "coverage": {"inspection_evidence": [{"file": "src/app.py"}]}}
    assert _complete_snapshot_from_local_git(tmp_path, review, "3" * 40) is True
    assert review["findings"] == [{"id": "F1"}]
    assert review["review_context"]["merge_base"] == "2" * 40
    assert review["coverage"]["changed_files"] == ["src/app.py"]


def test_missing_inspection_files_is_scoped_to_changed_snapshot_files():
    snapshot = _snapshot()
    review = {"coverage": {"inspection_evidence": [{"file": "a.py", "evidence": "read callers"}]}}
    assert _missing_inspection_files(review, snapshot) == ["b.py"]


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


def test_web_transport_parser_accumulates_json_patch_deltas():
    class Response:
        def iter_lines(self):
            yield b'data: {"conversation_id":"conv-2"}'
            yield b'data: {"o":"patch","v":[{"o":"append","p":"/message/content/parts/0","v":"{\\"verdict\\":\\"APPROVED\\","}]}'
            yield b'data: {"v":"\\"review_context\\":{}}"}'
            yield b'data: [DONE]'

    text, meta = parse_sse_assistant(Response())
    assert text == '{"verdict":"APPROVED","review_context":{}}'
    assert meta["conversation_id"] == "conv-2"


def test_extract_json_ignores_intermediate_tool_json_and_selects_review_object():
    review = _hardened_review()
    reply = (
        'progress {"path":"/GitHub/get_pull_request"}\n'
        + "```json\n"
        + json.dumps(review)
        + "\n```"
    )
    assert _extract_json(reply) == review


def test_extract_json_rejects_json_without_review_contract():
    with pytest.raises(BrowserlessReviewError, match="required final code-review object"):
        _extract_json('{"path":"/GitHub/get_pull_request"}')


def test_extract_json_prefers_last_review_object_after_incomplete_progress():
    first = {"verdict": "BLOCKED", "review_context": {}}
    second = _hardened_review()
    assert _extract_json(json.dumps(first) + "\n" + json.dumps(second)) == second


def test_changed_files_mapping_is_normalized_only_when_keys_are_paths():
    assert _changed_files_for_snapshot({"coverage": {"changed_files": {"src/a.py": {}, "README.md": {}}}}) == (
        ["src/a.py", "README.md"],
        True,
    )
    assert _changed_files_for_snapshot({"coverage": {"changed_files": {"count": 2}}}) == (None, False)


def test_requirement_ids_keep_numeric_and_suffixed_ids_distinct_and_canonical():
    assert _canonical_requirement_id("fr018") == "FR-018"
    assert _canonical_requirement_id("FR-018a") == "FR-018A"
    assert _requirement_ids("FR-018 is numeric; FR-018a is its predecessor contract") == (
        "FR-018",
        "FR-018A",
    )


def test_spec_requirement_inventory_contains_all_active_ids_including_fr_018a():
    spec = Path(__file__).parents[1] / "specs" / "001-single-skill-baseline" / "spec.md"
    ids = _requirement_ids(spec.read_text(encoding="utf-8"))
    expected = tuple(
        [f"FR-{index:03d}" for index in range(1, 31) if index != 18]
        + ["FR-018", "FR-018A"]
        + [f"SC-{index:03d}" for index in range(1, 13)]
    )
    assert ids == tuple(sorted(expected))
    assert len(ids) == 43
    assert "FR-018" in ids
    assert "FR-018A" in ids


def test_requirement_repair_merges_only_requirements_from_continuation():
    original = _hardened_review()
    original["verdict"] = "CHANGES_REQUIRED"
    original["findings"] = [{
        "id": "R001-001",
        "authority_ref": "SPEC FR-018a",
        "implementation_evidence": "original evidence",
        "failure_scenario": "original failure",
        "required_change": "original change",
    }]
    repaired = {
        "verdict": "BLOCKED",
        "findings": [{"id": "R999-999", "evidence": "rewritten"}],
        "review_context": {"head_sha": "rewritten"},
        "coverage": {
            "changed_files": ["rewritten.py"],
            "inspection_evidence": [{"file": "rewritten.py", "evidence": "rewritten"}],
            "requirements": [
                {"id": "fr-018", "status": "PASS", "evidence": ["numeric"]},
                {"id": "fr-018a", "status": "PASS", "evidence": ["suffix"]},
            ],
        },
    }

    merged = _merge_requirement_repair(original, repaired, {"FR-018", "FR-018A"})

    assert merged["verdict"] == "CHANGES_REQUIRED"
    assert merged["findings"] == original["findings"]
    assert merged["review_context"] == original["review_context"]
    assert merged["coverage"]["changed_files"] == original["coverage"]["changed_files"]
    assert merged["coverage"]["inspection_evidence"] == original["coverage"]["inspection_evidence"]
    assert [item["id"] for item in merged["coverage"]["requirements"]] == ["FR-018", "FR-018A"]


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


def test_web_transport_parser_detects_confirmation_on_nonstandard_message_envelope():
    class Response:
        def iter_lines(self):
            yield b'data: {"v":{"message":{"id":"assistant-2","author":{"role":"assistant"},"content":{"content_type":"code","text":"github call"}}}}'
            yield b'data: {"v":{"message":{"id":"tool-2","author":{"role":"tool","name":"web.run"},"content":{"content_type":"text","parts":[""]},"metadata":{"jit_plugin_data":{"from_server":{"type":"confirm_action","actions":[{"type":"allow","target_message_id":"assistant-2"}]}}}}}}'
            yield b'data: [DONE]'

    _, pending = parse_sse_assistant(Response())

    assert pending["pending_allow"] == {
        "target_message_id": "assistant-2",
        "parent_message_id": "tool-2",
    }
    assert pending["authorization_required"] is True


def test_connector_allow_falls_back_to_legacy_conversation_route(monkeypatch):
    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = "not found" if status_code >= 400 else ""

        def iter_lines(self):
            yield b'data: {"v":{"message":{"id":"assistant-allow","author":{"role":"assistant"},"content":{"parts":["{\\"verdict\\":\\"BLOCKED\\"}"]}}}}'
            yield b'data: [DONE]'

    class Session:
        def __init__(self):
            self.paths = []

        def post(self, url, **kwargs):
            self.paths.append(url)
            return Response(404 if url.endswith("/f/conversation") else 200)

    session = Session()
    monkeypatch.setattr("speckit_powerpack.chatgpt_pow_probe.get_chat_requirements", lambda *_: {
        "token": "sentinel",
        "proof_token": "proof",
        "turnstile_token": "turnstile",
    })

    text, _ = send_connector_allow(
        session,
        {"token": "sentinel", "proof_token": "proof", "turnstile_token": "turnstile"},
        conversation_id="conversation",
        parent_message_id="parent",
        target_message_id="target",
        project_id="g-p-project",
        model="gpt-5-6-thinking",
        account_id="account",
    )

    assert session.paths == [
        "https://chatgpt.com/backend-api/f/conversation",
        "https://chatgpt.com/backend-api/conversation",
    ]
    assert text


def test_review_prompt_binds_project_spec_snapshot_and_github_app():
    prompt = _review_prompt(
        connector_id="connector_github",
        snapshot=_snapshot(),
        spec_context="FR-001 requirement\nSC-002 success criterion",
        protocol="schema 2.0 protocol",
        user_instruction="review it",
        previous_review="",
    )
    assert "plugin:connector_github" in prompt
    assert '"snapshot_sha256": "' + "4" * 64 + '"' in prompt
    assert "CHATGPT PROJECT CONTEXT" not in prompt
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
        spec=type("Spec", (), {"spec_id": "SPEC-12", "serialized": "FR-001"})(),
        snapshot=snapshot,
        project=ProjectBinding("g-p-test", "Example", None),
        protocol="protocol-v3",
        previous_review=None,
        round_number=1,
        attempt=1,
        segment=1,
        master_prompt="MASTER CONTRACT",
        current_head_sha="3" * 40,
    )
    prompt = _master_review_prompt("MASTER CONTRACT", packet, target=PullRequestTarget("owner/repo", 12, "https://github.com/owner/repo/pull/12"))
    assert "POWERPACK MASTER CODE REVIEW v1.2" in prompt
    assert "Review Evidence Package" in prompt
    assert "POWERPACK_REVIEW_PACKET" not in prompt
    assert len(prompt) < 700
    assert packet["review_id"] == "owner/repo#12:SPEC-12:implement-review"
    assert packet["master_prompt"]["sha256"]
    assert packet["expected_requirement_ids"] == ["FR-001"]
    assert packet["project"] == {
        "project_id": "g-p-test",
        "project_name": "Example",
        "authority": "bound ChatGPT Project; context resolved by Web",
    }
    assert "project_context" not in packet
    assert "one final JSON object" in prompt
    assert "blocked_reason" in prompt
    assert "Name the bound Project and summarize its mission" not in prompt


def test_review_bundle_persists_structured_inputs_and_hash_manifest(tmp_path: Path):
    packet = {"repository": "owner/repo", "expected_requirement_ids": ["FR-001"]}
    manifest = _write_review_bundle(
        bundle_dir=tmp_path / "review-bundle",
        master_prompt="master",
        protocol="protocol",
        evidence_contract="github evidence",
        packet=packet,
        spec_context="FR-001 requirement",
        previous_review=None,
    )
    assert manifest["execution_model"] == "one-message-with-structured-artifacts"
    assert (tmp_path / "review-bundle" / "instructions.md").is_file()
    assert json.loads((tmp_path / "review-bundle" / "packet.json").read_text()) == packet
    assert {item["name"] for item in manifest["artifacts"]} == {
        "output-schema.json", "master-prompt.md", "packet.json", "protocol.md", "github-evidence-contract.md", "spec-artifacts.md", "instructions.md"
    }
    assert (tmp_path / "review-bundle" / "manifest.json").is_file()


def test_external_blocked_review_is_classified_as_pending():
    assert _external_blocked_reasons({"verdict": "BLOCKED", "blocked_reason": ["MISSING_GITHUB_SNAPSHOT"]}) == [
        "MISSING_GITHUB_SNAPSHOT"
    ]
    assert _external_blocked_reasons({"verdict": "BLOCKED", "coverage": {"blocked_reason": ["MISSING_TOOL"]}}) == [
        "MISSING_TOOL"
    ]
    assert _external_blocked_reasons({"verdict": "BLOCKED", "blocked_reason": ["IMPLEMENTATION_DEFECT"]}) == []
    inferred = _external_blocked_reasons({
        "verdict": "BLOCKED",
        "coverage": {
            "changed_files": [],
            "inspection_evidence": [],
            "context_gaps": ["The immutable changed-file inventory was unavailable."],
        },
    })
    assert inferred == ["MISSING_CHANGED_FILES", "MISSING_GITHUB_SNAPSHOT"]


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
