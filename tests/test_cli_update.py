from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from speckit_powerpack import cli


def _args(tmp_path: Path, **overrides):
    values = {
        "path": str(tmp_path),
        "check": False,
        "project_only": False,
        "reset_config": False,
        "repository": None,
        "ref": None,
        "integration": None,
        "bootstrap_speckit": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_check_only_prints_status_without_install(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(cli, "check_update", lambda: {"status": "CURRENT", "ref": "main"})
    called = []
    monkeypatch.setattr(cli, "apply_self_update", lambda repository, ref: called.append((repository, ref)))
    cli.cmd_update(_args(tmp_path, check=True))
    assert called == []
    assert '"CURRENT"' in capsys.readouterr().out


def test_project_only_rematerializes_without_self_update(monkeypatch, tmp_path: Path):
    calls = []
    (tmp_path / ".specify").mkdir()
    monkeypatch.setattr(cli, "project_integration", lambda project: "codex")
    monkeypatch.setattr(cli, "apply_self_update", lambda repository, ref: calls.append("self-update"))
    monkeypatch.setattr(
        cli,
        "install_powerpack",
        lambda path, integration, initialize, bootstrap, reset_config=False: calls.append(
            (path, integration, initialize, bootstrap, reset_config)
        ),
    )
    cli.cmd_update(_args(tmp_path, project_only=True, reset_config=True))
    assert "self-update" not in calls
    assert calls == [(str(tmp_path.resolve()), "codex", False, False, True)]


def test_full_update_uses_effective_source_then_refreshes_project(monkeypatch, tmp_path: Path):
    calls = []
    (tmp_path / ".specify").mkdir()
    monkeypatch.setattr(cli, "effective_source", lambda: {
        "repository": "https://github.com/ds1david/speckit-powerpack.git",
        "ref": "main",
    })
    monkeypatch.setattr(cli, "apply_self_update", lambda repository, ref: calls.append((repository, ref)))
    monkeypatch.setattr(cli, "project_integration", lambda project: "claude")
    monkeypatch.setattr(cli, "install_powerpack", lambda *args, **kwargs: calls.append((args, kwargs)))
    cli.cmd_update(_args(tmp_path))
    assert calls[0] == ("https://github.com/ds1david/speckit-powerpack.git", "main")
    assert calls[1][1]["initialize"] is False
