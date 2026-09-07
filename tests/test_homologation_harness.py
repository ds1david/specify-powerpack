from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "homologation" / "homologate.py"
SPEC = importlib.util.spec_from_file_location("powerpack_homologate", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_default_ref_is_browserless_baseline():
    args = MODULE.parse_args(["H1"])
    assert args.powerpack_ref == "feat/chatgpt-project-provider-no-browser"
    assert args.install_source == "remote"


def test_project_can_come_from_environment(monkeypatch):
    monkeypatch.setenv("POWERPACK_CHATGPT_PROJECT", "g-p-test")
    args = MODULE.parse_args(["H2"])
    assert args.chatgpt_project == "g-p-test"


def test_wsl_local_clone_default_is_under_workspace():
    args = MODULE.parse_args(["H1"])
    assert Path(args.powerpack_repo).name == "speckit-powerpack"
    assert Path(args.powerpack_repo).parent.name == "workspace"


def test_strict_clean_mode_is_opt_in():
    assert MODULE.parse_args(["H1"]).require_clean is False
    assert MODULE.parse_args(["H1", "--require-clean"]).require_clean is True
