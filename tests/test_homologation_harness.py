from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "homologation" / "homologate.py"
SCRIPT_DIR = SCRIPT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SPEC = importlib.util.spec_from_file_location("powerpack_homologate", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

RUN_SCRIPT = SCRIPT_DIR / "run.py"
RUN_SPEC = importlib.util.spec_from_file_location("powerpack_homologation_run", RUN_SCRIPT)
assert RUN_SPEC and RUN_SPEC.loader
RUN_MODULE = importlib.util.module_from_spec(RUN_SPEC)
sys.modules[RUN_SPEC.name] = RUN_MODULE
RUN_SPEC.loader.exec_module(RUN_MODULE)


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


def test_materialize_resets_managed_config_before_scenario_setup(tmp_path, monkeypatch):
    args = MODULE.parse_args(
        [
            "H1",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(tmp_path / "evidence"),
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)
    monkeypatch.setattr(MODULE.Harness, "materialize", lambda self, integration: None)

    seen: list[list[str]] = []

    def fake_command(cmd, *, label, cwd=None, expected_codes=(0,)):
        seen.append(list(cmd))
        assert label == "powerpack-config-reset"
        return subprocess.CompletedProcess(cmd, 0, stdout='{"status":"PROJECT_REFRESHED"}', stderr="")

    monkeypatch.setattr(harness, "command", fake_command)
    monkeypatch.setattr(
        harness,
        "read_review",
        lambda: {
            "provider": "codex",
            "chatgpt_web": {
                "required": False,
                "enabled": False,
                "mode": "disabled",
                "project_alias": None,
                "project_id": None,
                "project_name": None,
                "project_url": None,
                "account_label": None,
                "authorization": None,
            },
        },
    )

    harness.materialize("codex")

    assert seen
    reset = seen[0]
    assert "update" in reset
    assert "--project-only" in reset
    assert "--force" in reset
    assert "--yes" in reset
    assert "--reset-config" in reset
    assert "--integration" in reset
    assert "codex" in reset
    assert any(
        check.name == "powerpack-config-reset-state" and check.status == MODULE.PASS
        for check in harness.checks
    )


def test_materialize_fails_if_reset_leaves_stale_project_binding(tmp_path, monkeypatch):
    args = MODULE.parse_args(
        [
            "H1",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(tmp_path / "evidence"),
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)
    monkeypatch.setattr(MODULE.Harness, "materialize", lambda self, integration: None)
    monkeypatch.setattr(
        harness,
        "command",
        lambda cmd, *, label, cwd=None, expected_codes=(0,): subprocess.CompletedProcess(
            cmd, 0, stdout="reset", stderr=""
        ),
    )
    monkeypatch.setattr(
        harness,
        "read_review",
        lambda: {
            "provider": "chatgpt-project",
            "chatgpt_web": {
                "project_id": "g-p-stale",
                "project_url": "https://chatgpt.com/g/g-p-stale/project",
            },
        },
    )

    with pytest.raises(MODULE.HarnessError, match="stale Project binding"):
        harness.materialize("codex")


def test_h2_bind_failure_is_recorded_and_stops_before_smoke(tmp_path, monkeypatch):
    evidence_root = tmp_path / "evidence"
    args = MODULE.parse_args(
        [
            "H2",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(evidence_root),
            "--chatgpt-project",
            "g-p-test",
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)
    monkeypatch.setattr(harness, "materialize", lambda integration: None)

    labels: list[str] = []

    def fake_command(cmd, *, label, cwd=None, expected_codes=(0,)):
        labels.append(label)
        if label == "project-bind":
            return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="bind failed")
        raise AssertionError(f"unexpected command after failed bind: {label}")

    monkeypatch.setattr(harness, "command", fake_command)

    with pytest.raises(MODULE.HarnessError, match="bind failed"):
        harness.run_h2()

    assert "project-bind" in labels
    assert "doctor-after-bind" not in labels
    assert "both-smoke" not in labels
    assert any(
        check.name == "chatgpt-project-bind" and check.status == MODULE.FAIL
        for check in harness.checks
    )


def test_h2_bind_invalid_persisted_state_is_fail_fast(tmp_path, monkeypatch):
    args = MODULE.parse_args(
        [
            "H2",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(tmp_path / "evidence"),
            "--chatgpt-project",
            "g-p-test",
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)

    def fake_command(cmd, *, label, cwd=None, expected_codes=(0,)):
        assert label == "project-bind"
        return subprocess.CompletedProcess(cmd, 0, stdout="bound", stderr="")

    monkeypatch.setattr(harness, "command", fake_command)
    monkeypatch.setattr(
        harness,
        "read_review",
        lambda: {
            "provider": "codex",
            "chatgpt_web": {
                "required": False,
                "enabled": False,
                "mode": "disabled",
                "project_id": None,
                "project_url": None,
            },
        },
    )

    with pytest.raises(MODULE.HarnessError, match="did not persist"):
        harness.bind_chatgpt_project()

    assert any(
        check.name == "chatgpt-project-bind-state" and check.status == MODULE.FAIL
        for check in harness.checks
    )


def test_h2_bind_success_records_command_and_state(tmp_path, monkeypatch):
    args = MODULE.parse_args(
        [
            "H2",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(tmp_path / "evidence"),
            "--chatgpt-project",
            "g-p-test",
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)

    def fake_command(cmd, *, label, cwd=None, expected_codes=(0,)):
        assert label == "project-bind"
        return subprocess.CompletedProcess(cmd, 0, stdout="bound", stderr="")

    monkeypatch.setattr(harness, "command", fake_command)
    monkeypatch.setattr(
        harness,
        "read_review",
        lambda: {
            "provider": "chatgpt-project",
            "chatgpt_web": {
                "required": True,
                "enabled": True,
                "mode": "backend-api",
                "project_id": "g-p-test",
                "project_url": "https://chatgpt.com/g/g-p-test/project",
            },
        },
    )

    review = harness.bind_chatgpt_project()

    assert review["provider"] == "chatgpt-project"
    assert any(
        check.name == "chatgpt-project-bind" and check.status == MODULE.PASS
        for check in harness.checks
    )
    assert any(
        check.name == "chatgpt-project-bind-state" and check.status == MODULE.PASS
        for check in harness.checks
    )


def test_h5_environment_probe_never_invokes_codex(tmp_path, monkeypatch):
    args = MODULE.parse_args(
        [
            "H5",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(tmp_path / "evidence"),
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)
    harness.scenario = "common"
    invoked: list[str] = []

    monkeypatch.setattr(RUN_MODULE.shutil, "which", lambda name: f"/bin/{name}")

    def fake_run(cmd, *, text, capture_output, shell):
        invoked.append(cmd[0])
        return subprocess.CompletedProcess(cmd, 0, stdout=f"{cmd[0]} version", stderr="")

    monkeypatch.setattr(RUN_MODULE.subprocess, "run", fake_run)
    harness.capture_environment()

    assert "copilot" in invoked
    assert "codex" not in invoked


def test_copilot_review_is_programmatic_read_only_and_has_no_codex_or_chatgpt(tmp_path, monkeypatch):
    spec_dir = tmp_path / "specs" / "demo"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Demo\n", encoding="utf-8")
    args = MODULE.parse_args(
        [
            "H5",
            "--project-path",
            str(tmp_path),
            "--evidence-root",
            str(tmp_path / "evidence"),
        ]
    )
    harness = RUN_MODULE.BindingAwareHarness(args)
    harness.scenario = "H5"
    captured: list[str] = []

    def fake_command(cmd, *, label, cwd=None, expected_codes=(0,)):
        captured.extend(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="No blocking findings.\nPOWERPACK_COPILOT_REVIEW_1_OK\n",
            stderr="",
        )

    monkeypatch.setattr(harness, "command", fake_command)
    harness._copilot_review(
        number=1,
        branch="spec/demo",
        spec_dir=spec_dir,
        marker=RUN_MODULE.COPILOT_REVIEW_1_MARKER,
    )

    assert captured[0] == "copilot"
    assert "-p" in captured
    assert "-s" in captured
    assert "--no-ask-user" in captured
    assert any(arg.startswith("--allow-tool=read,") for arg in captured)
    assert any("--deny-tool=write,memory,url" in arg for arg in captured)
    assert "codex" not in captured
    assert "chatgpt" not in [item.casefold() for item in captured if not item.startswith("/review")]
