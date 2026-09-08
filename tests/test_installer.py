from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "install.py"
spec = importlib.util.spec_from_file_location("powerpack_installer", MODULE_PATH)
assert spec and spec.loader
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_installer_bootstraps_cli_then_initializes_project(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    monkeypatch.setattr(installer, "ensure_python", lambda: None)
    monkeypatch.setattr(installer, "ensure_git", lambda: None)
    monkeypatch.setattr(installer, "uv_command", lambda: ["uv"])
    monkeypatch.setattr(installer, "resolve_powerpack_binary", lambda uv: "specify-powerpack")
    monkeypatch.setattr(installer, "run", lambda argv, **kwargs: calls.append(list(argv)))

    code = installer.main([
        "--repository", "https://github.com/example/powerpack.git",
        "--ref", "abc123",
        "--project", str(tmp_path),
        "--integration", "codex",
    ])

    assert code == 0
    assert calls == [
        ["uv", "tool", "install", "--force", "git+https://github.com/example/powerpack.git@abc123"],
        ["specify-powerpack", "init", str(tmp_path), "--integration", "codex"],
    ]


def test_installer_reset_config_is_explicit(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    monkeypatch.setattr(installer, "ensure_python", lambda: None)
    monkeypatch.setattr(installer, "ensure_git", lambda: None)
    monkeypatch.setattr(installer, "uv_command", lambda: ["uv"])
    monkeypatch.setattr(installer, "resolve_powerpack_binary", lambda uv: "specify-powerpack")
    monkeypatch.setattr(installer, "run", lambda argv, **kwargs: calls.append(list(argv)))

    assert installer.main(["--project", str(tmp_path), "--reset-config"]) == 0
    assert calls[-1][-1] == "--reset-config"


def test_installer_brand_and_repository_are_canonical():
    assert installer.PRODUCT_NAME == "Specify PowerPack"
    assert installer.CANONICAL_CLI == "specify-powerpack"
    assert installer.LEGACY_CLI == "speckit-powerpack"
    assert installer.DEFAULT_REPOSITORY == "https://github.com/ds1david/specify-powerpack.git"


def test_shell_wrappers_delegate_to_python_installer():
    shell = (ROOT / "install.sh").read_text(encoding="utf-8")
    powershell = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "install.py" in shell
    assert "install.py" in powershell
    assert "playwright" not in shell.casefold()
    assert "playwright" not in powershell.casefold()
