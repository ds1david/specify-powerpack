"""SPEC-001 Single Skill Baseline — exact-set regression guard.

Encodes the invariant that the `powerpack-core` preset provides exactly one
command, `speckit.implement-review`. Adding or restoring a second command here
must fail these tests and force an explicit scope decision (spec §Regression Guard,
FR-017 / FR-011 / FR-004).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from speckit_powerpack import cli

ROOT = Path(__file__).parents[1]
PRESET_YML = ROOT / "src" / "speckit_powerpack" / "assets" / "presets" / "powerpack-core" / "preset.yml"

EXPECTED = {"speckit.implement-review"}

# Removed PowerPack command names (dotted form — distinct from upstream Spec Kit's
# hyphenated `speckit-implement` / `speckit-converge`, which stay).
REMOVED_COMMAND_NAMES = (
    "speckit.implement",
    "speckit.converge",
    "speckit.checklist-converge",
    "speckit.full-cycle",
    "speckit.debt-create",
    "speckit.debt-list",
    "speckit.debt-consult",
    "speckit.debt-start",
    "speckit.debt-close",
)

needs_specify = pytest.mark.skipif(
    not shutil.which("specify"),
    reason="real Spec Kit CLI ('specify') not on PATH — the installed-composition job provides it",
)


def _installed_powerpack_command_names(project: Path) -> set[str]:
    """Install-time enumeration (contracts/command-inventory.md): the command
    files Spec Kit materialised for the `powerpack-core` preset after
    `install_components()` ran the real `specify preset add`."""
    commands = project / ".specify" / "presets" / "powerpack-core" / "commands"
    return {p.stem for p in commands.glob("*.md")} if commands.is_dir() else set()


def _real_install(project: Path) -> None:
    """A real installation composition: `specify init` (agent-tool check skipped —
    CI has no Codex/Claude CLI) then `install_powerpack` runs the real
    `specify preset add` / `extension add`."""
    subprocess.run(
        ["specify", "init", "--here", "--integration", "codex", "--force", "--ignore-agent-tools"],
        cwd=project, check=True, capture_output=True, text=True,
    )
    cli.install_powerpack(str(project), "codex", initialize=False, bootstrap=False)


def parse_preset_command_names(path: Path) -> set[str]:
    """Canonical enumeration: the `name:` of every `type: "command"` entry under
    `provides.templates` in preset.yml (contracts/command-inventory.md)."""
    names: set[str] = set()
    current_type: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = re.match(r'-?\s*type:\s*"([^"]+)"', line)
        if m:
            current_type = m.group(1)
            continue
        m = re.match(r'name:\s*"([^"]+)"', line)
        if m and current_type == "command":
            names.add(m.group(1))
            current_type = None
    return names


def test_registration_command_set_is_exactly_implement_review():
    assert parse_preset_command_names(PRESET_YML) == EXPECTED


def test_preset_yml_references_no_other_command_file():
    text = PRESET_YML.read_text(encoding="utf-8")
    files = set(re.findall(r'file:\s*"(commands/[^"]+)"', text))
    assert files == {"commands/speckit.implement-review.md"}


def test_installed_support_has_no_removed_command_assets(tmp_path: Path):
    (tmp_path / ".specify").mkdir()
    cli.install_support(tmp_path, "codex")
    base = tmp_path / ".specify" / "powerpack"
    installed_bin = sorted(p.name for p in (base / "bin").glob("*.py"))
    assert installed_bin == ["capabilities.py", "powerpack.py", "review_protocol.py"]
    for gone in (
        "bin/debt.py",
        "bin/full_cycle.py",
        "technical-debt-policy.md",
        "technical-debt-template.md",
        "technical-debt.json",
        "full-cycle.json",
    ):
        assert not (base / gone).exists(), gone


def test_update_prunes_retired_removed_command_state(tmp_path: Path):
    """R001-001 (round 3): a normal refresh of an already-installed project must
    remove retired removed-command runtimes/config and strip stale routing /
    prerequisite keys — without --reset-config — while preserving the Project
    binding and non-removed-command settings (FR-003 / FR-012)."""
    base = tmp_path / ".specify" / "powerpack"
    (base / "bin").mkdir(parents=True)
    for relative in cli.OBSOLETE_POWERPACK_PATHS:
        (base / relative).write_text("stale\n", encoding="utf-8")
    (base / "model-routing.json").write_text(json.dumps({
        "active_integration": "codex",
        "stages": {"implement-review": "orchestration", "full-cycle": "x", "debt-create": "y"},
        "stage_reasons": {"implement-review": "…", "full-cycle": "…"},
        "effort": {"codex": {"reviewer": "xhigh"}},
    }), encoding="utf-8")
    (base / "prerequisites.json").write_text(json.dumps({
        "schema_version": 1,
        "mode": "strict",
        "steps": {
            "implement-review": [{"step": "implement", "statuses": ["COMPLETED"]}],
            "checklist-converge": [{"step": "checklist", "statuses": ["COMPLETED"]}],
        },
    }), encoding="utf-8")
    # sentinels that must survive an update
    (base / "quality-gates.json").write_text(
        json.dumps({"schema_version": 1, "custom_command": ["mytool", "verify"]}), encoding="utf-8"
    )
    (base / "review.json").write_text(json.dumps({
        "provider": "chatgpt-project",
        "chatgpt_project": {
            "project_id": "g-p-sentinel123",
            "project_name": "My Project",
            "project_url": "https://chatgpt.com/g/g-p-sentinel123/project",
        },
    }), encoding="utf-8")

    cli.install_support(tmp_path, "codex")  # no reset_config

    for relative in cli.OBSOLETE_POWERPACK_PATHS:
        assert not (base / relative).exists(), relative
    routing = json.loads((base / "model-routing.json").read_text(encoding="utf-8"))
    assert set(routing["stages"]) == {"implement-review"}
    assert set(routing["stage_reasons"]) == {"implement-review"}
    prereq = json.loads((base / "prerequisites.json").read_text(encoding="utf-8"))
    assert prereq["schema_version"] >= 2
    assert prereq["steps"] == {"implement-review": [{"check": "implementation-evidence"}]}
    assert prereq["mode"] == "strict"
    quality = json.loads((base / "quality-gates.json").read_text(encoding="utf-8"))
    assert quality["custom_command"] == ["mytool", "verify"]
    review = json.loads((base / "review.json").read_text(encoding="utf-8"))
    assert review["chatgpt_project"]["project_id"] == "g-p-sentinel123"


def test_removed_command_names_are_unknown_to_the_runtime_parser():
    """FR-014 behavioural check: a removed command name is not a registered
    subcommand of the installed runtime CLI."""
    import importlib.util

    rt_path = ROOT / "src" / "speckit_powerpack" / "assets" / "runtime" / "powerpack_runtime.py"
    spec = importlib.util.spec_from_file_location("powerpack_runtime_bc", rt_path)
    assert spec and spec.loader
    rt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rt)
    parser = rt.build_parser()
    subparsers_action = next(
        a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction"
    )
    top_level = set(subparsers_action.choices)
    # The `implement begin/end` delta-capture subcommand of the removed
    # `speckit.implement` wrap is gone; no removed command is a runtime verb.
    assert "implement" not in top_level
    assert not hasattr(rt, "cmd_implement_begin")
    assert not hasattr(rt, "cmd_implement_end")
    assert not hasattr(rt, "powerpack_debt")
    assert not hasattr(rt, "powerpack_full_cycle")


def test_model_routing_stage_set_is_exactly_implement_review():
    routing = json.loads(
        (ROOT / "src" / "speckit_powerpack" / "assets" / "config" / "default-model-routing.json").read_text("utf-8")
    )
    assert set(routing["stages"]) == {"implement-review"}


@needs_specify
def test_installed_powerpack_command_namespace_is_exactly_implement_review(tmp_path: Path):
    """R001-003 (round 3) / FR-011 installed-side equality: enumerate the command
    namespace a *real* installation composition materialises (post `specify preset
    add`), not just the source `preset.yml`."""
    _real_install(tmp_path)
    assert _installed_powerpack_command_names(tmp_path) == EXPECTED
    base = tmp_path / ".specify" / "powerpack"
    for relative in cli.OBSOLETE_POWERPACK_PATHS:
        assert not (base / relative).exists(), relative


@needs_specify
def test_removed_command_names_are_undispatchable_after_a_real_install(tmp_path: Path):
    """R001-004 (round 3) / FR-014: after a clean install, every removed PowerPack
    command name resolves to nothing at the command layer — no materialised
    command file anywhere under the project, and no silent redirect to
    `implement-review`."""
    _real_install(tmp_path)
    command_files = {
        p.name
        for p in tmp_path.rglob("*")
        if p.is_file() and p.suffix == ".md" and "commands" in p.parts
    }
    for name in REMOVED_COMMAND_NAMES:
        assert f"{name}.md" not in command_files, name
    # the one PowerPack command that DOES exist is implement-review, and it is not
    # a redirect target for the removed names (distinct file, distinct name)
    assert "speckit.implement-review.md" in command_files
    base = tmp_path / ".specify" / "powerpack"
    assert not (base / "bin" / "debt.py").exists()
    assert not (base / "bin" / "full_cycle.py").exists()
