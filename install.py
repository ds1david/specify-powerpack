#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


DEFAULT_REPOSITORY = "https://github.com/ds1david/speckit-powerpack.git"
DEFAULT_REF = "main"


class InstallError(RuntimeError):
    pass


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(argv), flush=True)
    proc = subprocess.run(argv, text=True, check=False)
    if check and proc.returncode != 0:
        raise InstallError(f"Command failed with exit code {proc.returncode}: {' '.join(argv)}")
    return proc


def ensure_python() -> None:
    if sys.version_info < (3, 11):
        raise InstallError(
            f"Python 3.11+ is required; running {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}."
        )


def ensure_git() -> None:
    if not shutil.which("git"):
        raise InstallError("Git is required and was not found on PATH.")


def uv_command() -> list[str]:
    binary = shutil.which("uv")
    if binary:
        return [binary]
    print("uv was not found; bootstrapping it with the current Python interpreter.")
    run([sys.executable, "-m", "pip", "install", "--user", "uv"])
    binary = shutil.which("uv")
    if binary:
        return [binary]
    probe = subprocess.run([sys.executable, "-m", "uv", "--version"], check=False)
    if probe.returncode == 0:
        return [sys.executable, "-m", "uv"]
    raise InstallError(
        "uv was installed but is not executable. Add the Python user scripts directory to PATH and run the installer again."
    )


def resolve_powerpack_binary(uv: list[str]) -> str:
    binary = shutil.which("speckit-powerpack")
    if binary:
        return binary
    proc = subprocess.run([*uv, "tool", "dir", "--bin"], text=True, capture_output=True, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        candidate = Path(proc.stdout.strip()) / ("speckit-powerpack.exe" if sys.platform == "win32" else "speckit-powerpack")
        if candidate.is_file():
            return str(candidate)
    raise InstallError(
        "PowerPack was installed by uv but the executable is not on PATH. Run 'uv tool update-shell', restart the shell, then run 'speckit-powerpack init'."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap SpecKit PowerPack and optionally initialize it in one repository."
    )
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--project", help="Optional project directory to initialize immediately")
    parser.add_argument("--integration", choices=["codex", "claude"], default="codex")
    parser.add_argument("--reset-config", action="store_true")
    args = parser.parse_args(argv)

    try:
        ensure_python()
        ensure_git()
        uv = uv_command()
        source = f"git+{args.repository}@{args.ref}"
        run([*uv, "tool", "install", "--force", source])
        powerpack = resolve_powerpack_binary(uv)
        print(f"SpecKit PowerPack CLI installed: {powerpack}")
        if args.project:
            command = [powerpack, "init", str(Path(args.project).expanduser()), "--integration", args.integration]
            if args.reset_config:
                command.append("--reset-config")
            run(command)
        else:
            print("Next step:")
            print("  speckit-powerpack init <project-directory> --integration codex")
        print("After project installation, run 'codex login' and 'speckit-powerpack review setup --path <project>'.")
        return 0
    except InstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
