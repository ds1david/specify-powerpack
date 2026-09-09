from __future__ import annotations

import json
from pathlib import Path

from speckit_powerpack import cli


def test_install_support_materializes_browserless_project_contract(tmp_path: Path):
    (tmp_path / ".specify").mkdir()
    cli.install_support(tmp_path, "claude")
    base = tmp_path / ".specify" / "powerpack"

    for relative in (
        "bin/powerpack.py",
        "bin/capabilities.py",
        "bin/review_protocol.py",
        "deep-review-protocol.md",
    ):
        assert (base / relative).is_file(), relative

    # SPEC-001 single-skill baseline: removed-command assets must not land.
    for gone in (
        "bin/debt.py",
        "bin/full_cycle.py",
        "technical-debt-policy.md",
        "technical-debt-template.md",
        "technical-debt.json",
        "full-cycle.json",
    ):
        assert not (base / gone).exists(), gone

    review = json.loads((base / "review.json").read_text(encoding="utf-8"))
    assert review["schema_version"] == 5
    assert review["review_backend"] == "codex-apps-github"
    assert review["chatgpt_project"]["required"] is True
    assert review["chatgpt_project"]["authorization"] is None
    assert review["github_app"]["runtime"] == "codex_apps"
    assert review["github_app"]["allow_shell_fallback"] is False

    prereq = json.loads((base / "prerequisites.json").read_text(encoding="utf-8"))
    assert prereq["schema_version"] == 2
    assert "checklist-converge" not in prereq["steps"]
    assert prereq["steps"]["implement-review"] == [{"check": "implementation-evidence"}]
    assert '"statuses": ["COMPLETED"]' not in json.dumps(prereq)

    routing = json.loads((base / "model-routing.json").read_text(encoding="utf-8"))
    assert routing["active_integration"] == "claude"
    assert routing["stages"] == {"implement-review": "orchestration"}


def test_codex_install_materializes_terra_parent_and_sol_reviewer_defaults(tmp_path: Path):
    (tmp_path / ".specify").mkdir()
    cli.install_support(tmp_path, "codex")
    routing = json.loads((tmp_path / ".specify" / "powerpack" / "model-routing.json").read_text(encoding="utf-8"))
    assert routing["active_integration"] == "codex"
    assert routing["integrations"]["codex"]["coding"] == "gpt-5.6-terra"
    assert routing["integrations"]["codex"]["economical"] == "gpt-5.6-luna"
    assert routing["integrations"]["codex"]["reviewer"] == "gpt-5.6-sol"
    assert routing["effort"]["codex"]["reviewer"] == "xhigh"


def test_install_migrates_legacy_project_binding_without_browser_state(tmp_path: Path):
    (tmp_path / ".specify").mkdir()
    base = tmp_path / ".specify" / "powerpack"
    base.mkdir(parents=True)
    (base / "review.json").write_text(json.dumps({
        "provider": "chatgpt-project",
        "chatgpt_web": {
            "project_id": "g-p-test123",
            "project_name": "Project Example",
            "project_url": "https://chatgpt.com/g/test/project",
            "authorization": "codex-backend-api",
            "profile": "obsolete-browser-profile",
            "endpoint": "http://127.0.0.1:8080"
        }
    }), encoding="utf-8")

    cli.install_support(tmp_path, "codex")
    migrated = json.loads((base / "review.json").read_text(encoding="utf-8"))
    assert migrated["provider"] == "chatgpt-project"
    assert migrated["chatgpt_project"]["project_id"] == "g-p-test123"
    assert migrated["chatgpt_project"]["project_name"] == "Project Example"
    assert migrated["chatgpt_project"]["authorization"] == "codex-backend-api"
    assert "chatgpt_web" not in migrated
    rendered = json.dumps(migrated).casefold()
    assert "profile" not in rendered
    assert "127.0.0.1" not in rendered
    assert "web2api" not in rendered


def test_explicit_reset_drops_existing_project_binding(tmp_path: Path):
    (tmp_path / ".specify").mkdir()
    cli.install_support(tmp_path, "codex")
    base = tmp_path / ".specify" / "powerpack"
    path = base / "review.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["provider"] = "chatgpt-project"
    data["chatgpt_project"]["project_id"] = "g-p-test123"
    data["chatgpt_project"]["project_name"] = "Project Example"
    data["chatgpt_project"]["authorization"] = "codex-backend-api"
    path.write_text(json.dumps(data), encoding="utf-8")

    cli.install_support(tmp_path, "codex", reset_config=True)
    reset = json.loads(path.read_text(encoding="utf-8"))
    assert reset["provider"] == "unconfigured"
    assert reset["chatgpt_project"]["project_id"] is None
    assert reset["chatgpt_project"]["authorization"] is None
