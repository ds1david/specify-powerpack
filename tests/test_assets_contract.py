from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
ASSETS = ROOT / "src" / "speckit_powerpack" / "assets"
PRESET = ASSETS / "presets" / "powerpack-core"


def test_implement_review_has_single_canonical_asset():
    commands = PRESET / "commands"
    assert (commands / "speckit.implement-review.md").is_file()
    assert not (commands / "speckit.implement-review-v2.md").exists()
    preset = (PRESET / "preset.yml").read_text(encoding="utf-8")
    assert 'file: "commands/speckit.implement-review.md"' in preset


def test_debt_and_full_cycle_commands_are_packaged():
    commands = PRESET / "commands"
    for filename in (
        "speckit.full-cycle.md",
        "speckit.debt-create.md",
        "speckit.debt-list.md",
        "speckit.debt-consult.md",
        "speckit.debt-start.md",
        "speckit.debt-close.md",
    ):
        assert (commands / filename).is_file(), filename
    assert (ASSETS / "runtime" / "powerpack_debt.py").is_file()
    assert (ASSETS / "runtime" / "powerpack_full_cycle.py").is_file()


def test_review_defaults_are_browserless_project_and_github():
    review = json.loads((ASSETS / "config" / "default-review.json").read_text(encoding="utf-8"))
    assert review["schema_version"] == 5
    assert review["provider"] == "unconfigured"
    assert review["review_backend"] == "codex-apps-github"
    assert review["mode"] == "browserless"
    project = review["chatgpt_project"]
    assert project["required"] is True
    assert project["context_mode"] == "serialized"
    assert project["native_binding"] is False
    github = review["github_app"]
    assert github["required"] is True
    assert github["runtime"] == "codex_apps"
    assert github["explicit_app_mention"] is True
    assert github["allow_shell_fallback"] is False
    assert github["allow_web_search_fallback"] is False
    assert review["deep_review"]["schema_version"] == "2.0"
    assert review["deep_review"]["immutable_pr_manifest"] is True


def test_package_entrypoint_and_runtime_have_no_browser_stack():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'speckit-powerpack = "speckit_powerpack.cli:main"' in pyproject
    assert "playwright" not in pyproject.casefold()
    package = ROOT / "src" / "speckit_powerpack"
    for obsolete in (
        "chatgpt_web2api_backend.py",
        "cli_web2api_review.py",
        "cli_user_state.py",
        "desktop_browser_bridge.py",
        "web_review_smoke.py",
        "playwright_cli_compat.py",
        "playwright_eval_compat.py",
    ):
        assert not (package / obsolete).exists(), obsolete
    for required in (
        "chatgpt_project_provider.py",
        "github_connector_discovery.py",
        "codex_apps_runtime.py",
        "browserless_review.py",
        "review_context.py",
    ):
        assert (package / required).is_file(), required


def test_deep_review_protocol_and_validator_are_packaged():
    assert (ASSETS / "review" / "deep-review-protocol.md").is_file()
    assert (ASSETS / "runtime" / "powerpack_review_protocol.py").is_file()


def test_technical_debt_policy_forbids_review_escape_hatch():
    debt = json.loads((ASSETS / "config" / "default-technical-debt.json").read_text(encoding="utf-8"))
    policy = debt["creation_policy"]
    assert policy["forbid_active_review_findings"] is True
    assert policy["forbid_active_convergence_gaps"] is True
    assert policy["forbid_blockers"] is True
    assert policy["powerpack_policy_is_minimum_floor"] is True
    assert debt["storage_format"] == "markdown-v1"
    assert debt["template_path"] == ".specify/powerpack/technical-debt-template.md"


def test_full_cycle_defaults_preserve_safety_invariants():
    config = json.loads((ASSETS / "config" / "default-full-cycle.json").read_text(encoding="utf-8"))
    assert config["schema_version"] == 2
    assert config["behavior"]["same_spec_only"] is True
    assert config["behavior"]["stop_on_blocked"] is True
    assert config["behavior"]["allow_debt_escape_hatch"] is False
    assert config["behavior"]["explicit_initial_implement_required"] is True
    assert config["behavior"]["implement_review_owns_convergence"] is True
    assert "converge" not in config["phases"]


def test_implement_review_contract_routes_browserless_project_github_gate():
    text = (PRESET / "commands" / "speckit.implement-review.md").read_text(encoding="utf-8")
    assert "speckit-implement\n  -> speckit-implement-review" in text
    assert "speckit-converge" in text
    assert "gpt-5.6-sol/xhigh/read-only" in text
    assert "browserless ChatGPT Project + GitHub review" in text
    assert "[$github](app://<connector-id>)" in text
    assert "codex_apps MCP" in text
    assert "speckit-powerpack review run" in text
    assert "--pr <number-or-canonical-github-pr-url>" in text
    assert "local `HEAD == PR head SHA`" in text
    assert "Chrome, CDP, Playwright, Web2API" in text
    assert "BLOCKED_CONFIGURATION" in text


def test_model_routing_preserves_reviewer_profile():
    routing = json.loads((ASSETS / "config" / "default-model-routing.json").read_text(encoding="utf-8"))
    assert routing["schema_version"] == 2
    assert routing["stages"]["full-cycle"] == "orchestration"
    assert routing["stages"]["implement-review"] == "orchestration"
    assert routing["integrations"]["codex"]["coding"] == "gpt-5.6-terra"
    assert routing["integrations"]["codex"]["reviewer"] == "gpt-5.6-sol"
    assert routing["effort"]["codex"]["reviewer"] == "xhigh"
    assert routing["reviewer_contract"]["codex"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "sandbox": "read-only",
    }
