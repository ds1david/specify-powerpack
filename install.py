#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


PRODUCT_NAME = "Specify PowerPack"
CANONICAL_CLI = "specify-powerpack"
LEGACY_CLI = "speckit-powerpack"
DEFAULT_REPOSITORY = "https://github.com/ds1david/specify-powerpack.git"
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


def _candidate_binary_names() -> tuple[str, ...]:
    suffix = ".exe" if sys.platform == "win32" else ""
    return (f"{CANONICAL_CLI}{suffix}", f"{LEGACY_CLI}{suffix}")


def resolve_powerpack_binary(uv: list[str]) -> str:
    for command in (CANONICAL_CLI, LEGACY_CLI):
        binary = shutil.which(command)
        if binary:
            return binary
    proc = subprocess.run([*uv, "tool", "dir", "--bin"], text=True, capture_output=True, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        bin_dir = Path(proc.stdout.strip())
        for name in _candidate_binary_names():
            candidate = bin_dir / name
            if candidate.is_file():
                return str(candidate)
    raise InstallError(
        f"{PRODUCT_NAME} was installed by uv but the executable is not on PATH. "
        f"Run 'uv tool update-shell', restart the shell, then run '{CANONICAL_CLI} init'."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"Bootstrap {PRODUCT_NAME} and optionally initialize it in one repository."
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
        print(f"{PRODUCT_NAME} CLI installed: {powerpack}")
        if args.project:
            command = [powerpack, "init", str(Path(args.project).expanduser()), "--integration", args.integration]
            if args.reset_config:
                command.append("--reset-config")
            run(command)
        else:
            print("Next step:")
            print(f"  {CANONICAL_CLI} init <project-directory> --integration codex")
        print(
            "After project installation, run 'codex login' and "
            f"'{CANONICAL_CLI} review setup --path <project>'."
        )
        return 0
    except InstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
