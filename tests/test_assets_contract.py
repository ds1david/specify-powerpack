from __future__ import annotations

import json
import subprocess
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


def test_single_skill_baseline_removed_command_assets_are_gone():
    """SPEC-001: only `implement-review` survives in powerpack-core."""
    commands = PRESET / "commands"
    assert sorted(p.name for p in commands.glob("*.md")) == ["speckit.implement-review.md"]
    for gone in (
        "speckit.implement.md",
        "speckit.converge.md",
        "speckit.checklist-converge.md",
        "speckit.full-cycle.md",
        "speckit.debt-create.md",
        "speckit.debt-list.md",
        "speckit.debt-consult.md",
        "speckit.debt-start.md",
        "speckit.debt-close.md",
    ):
        assert not (commands / gone).exists(), gone
    assert not (ASSETS / "runtime" / "powerpack_debt.py").exists()
    assert not (ASSETS / "runtime" / "powerpack_full_cycle.py").exists()
    assert not (ASSETS / "config" / "default-full-cycle.json").exists()
    assert not (ASSETS / "config" / "default-technical-debt.json").exists()
    assert not (ASSETS / "policies").exists()
    assert not (ASSETS / "templates").exists()


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
    deep = review["deep_review"]
    assert deep["schema_version"] == "2.0"
    assert deep["immutable_pr_manifest"] is True
    assert deep["exact_changed_file_coverage"] is True
    assert deep["exact_requirement_coverage"] is True
    assert deep["inspection_evidence_required"] is True
    assert deep["context_gaps_block_approval"] is True


def test_package_entrypoint_and_runtime_have_no_browser_stack():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "specify-powerpack"' in pyproject
    assert 'specify-powerpack = "speckit_powerpack.cli:main"' in pyproject
    assert 'speckit-powerpack = "speckit_powerpack.cli:main"' in pyproject
    assert "https://github.com/ds1david/specify-powerpack" in pyproject
    assert "https://github.com/ds1david/speckit-powerpack" not in pyproject
    assert "playwright" not in pyproject.casefold()
    package = ROOT / "src" / "speckit_powerpack"
    for obsolete in (
        "chatgpt_web2api_backend.py",
        "cli_web2api_review.py",
        "cli_user_state.py",
        "desktop_browser_bridge.py",
        "web_review_smoke.py",
        "web_review_runner.py",
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


def test_installed_metadata_uses_specify_powerpack_brand():
    extension = (ASSETS / "extensions" / "powerpack-tools" / "extension.yml").read_text(encoding="utf-8")
    preset = (PRESET / "preset.yml").read_text(encoding="utf-8")
    assert 'name: "Specify PowerPack Tools"' in extension
    assert 'name: "Specify PowerPack Core"' in preset
    assert "ds1david/specify-powerpack" in extension
    assert "ds1david/specify-powerpack" in preset
    assert "ds1david/speckit-powerpack" not in extension
    assert "ds1david/speckit-powerpack" not in preset


def test_deep_review_protocol_and_validator_are_packaged():
    assert (ASSETS / "review" / "deep-review-protocol.md").is_file()
    assert (ASSETS / "runtime" / "powerpack_review_protocol.py").is_file()
    protocol = (ASSETS / "review" / "deep-review-protocol.md").read_text(encoding="utf-8")
    assert "exactly that same set of IDs" in protocol
    assert "coverage.inspection_evidence" in protocol
    assert "coverage.verdict_challenge" in protocol
    assert "coverage.context_gaps" in protocol
    assert "ChatGPT Project Web" not in protocol


def test_implement_review_contract_routes_browserless_project_github_gate():
    text = (PRESET / "commands" / "speckit.implement-review.md").read_text(encoding="utf-8")
    assert "speckit-implement\n  -> speckit-implement-review" in text
    assert "speckit-converge" in text
    assert "gpt-5.6-sol/xhigh/read-only" in text
    assert "browserless ChatGPT Project + GitHub review" in text
    assert "[$github](app://<connector-id>)" in text
    assert "codex_apps MCP" in text
    assert "specify-powerpack review run" in text
    assert "--pr <number-or-canonical-github-pr-url>" in text
    assert "local `HEAD == PR head SHA`" in text
    assert "Chrome, CDP, Playwright, Web2API" in text
    assert "BLOCKED_CONFIGURATION" in text


def test_installed_command_docs_reject_removed_browser_review_contracts():
    command_files = [
        ASSETS / "extensions" / "powerpack-tools" / "commands" / "doctor.md",
        ASSETS / "extensions" / "powerpack-tools" / "commands" / "update.md",
    ]
    forbidden = (
        "chatgpt-web2api",
        "playwright-consent",
        "review authorize",
        "review binding show",
        "browser profile",
        "web reviewer endpoint",
        "mandatory chatgpt project web review",
    )
    for path in command_files:
        text = path.read_text(encoding="utf-8").casefold()
        for marker in forbidden:
            assert marker not in text, f"{path.name} still references obsolete marker: {marker}"


def test_model_routing_preserves_reviewer_profile():
    routing = json.loads((ASSETS / "config" / "default-model-routing.json").read_text(encoding="utf-8"))
    assert routing["schema_version"] == 2
    assert routing["stages"] == {"implement-review": "orchestration"}
    assert routing["integrations"]["codex"]["coding"] == "gpt-5.6-terra"
    assert routing["integrations"]["codex"]["reviewer"] == "gpt-5.6-sol"
    assert routing["effort"]["codex"]["reviewer"] == "xhigh"
    assert routing["reviewer_contract"]["codex"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "sandbox": "read-only",
    }


def test_devcontainer_homologation_assets_present_and_valid():
    """The homologation devcontainer (T063): valid config + executable scripts,
    with the credential mounts declared and nothing baked into an image layer."""
    dc = ROOT / ".devcontainer"
    config = json.loads((dc / "devcontainer.json").read_text(encoding="utf-8"))
    mounts = " ".join(config.get("mounts", []))
    for host in (".codex", ".claude", ".config/gh"):
        assert host in mounts, f"expected a bind mount for ~/{host}"
    assert config["postCreateCommand"] == "bash .devcontainer/postcreate.sh"
    assert config["remoteEnv"]["SPECIFY_FEATURE"] == "001-single-skill-baseline"
    # exec bit: ask git (the working-tree stat is unreliable on a Windows checkout)
    staged = subprocess.run(
        ["git", "ls-files", "-s", "--", ".devcontainer/homologate.sh", ".devcontainer/postcreate.sh"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    modes = {line.split()[3].split("/")[-1]: line.split()[0] for line in staged.splitlines()}
    for script in ("homologate.sh", "postcreate.sh"):
        assert (dc / script).is_file(), script
        assert modes.get(script) == "100755", f"{script} must be tracked mode 100755, got {modes.get(script)}"
    homologate = (dc / "homologate.sh").read_text(encoding="utf-8")
    assert "review run" in homologate and "--timeout" in homologate
    assert "--effort" in homologate  # token-cost lever is exposed
    assert "git worktree remove --force" in homologate  # cleanup on exit
