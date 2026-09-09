"""SPEC-001 Single Skill Baseline — exact-set regression guard.

Encodes the invariant that the `powerpack-core` preset provides exactly one
command, `speckit.implement-review`. Adding or restoring a second command here
must fail these tests and force an explicit scope decision (spec §Regression Guard,
FR-017 / FR-011 / FR-004).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from speckit_powerpack import cli

ROOT = Path(__file__).parents[1]
PRESET_YML = ROOT / "src" / "speckit_powerpack" / "assets" / "presets" / "powerpack-core" / "preset.yml"

EXPECTED = {"speckit.implement-review"}


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
