#!/usr/bin/env python3
"""Launch Copilot or Spec Kit with repository-safe Copilot permission profiles.

This is development/homologation tooling. It does not persist environment variables,
modify shell profiles, or replace Copilot/Spec Kit configuration.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Profile:
    description: str
    deny_tools: tuple[str, ...]

    def cli_args(self) -> list[str]:
        args: list[str] = []
        for tool in self.deny_tools:
            args.append(f"--deny-tool={tool}")
        return args


REMOTE_GUARDRAILS = (
    "shell(git push)",
    "shell(gh pr merge)",
    "shell(gh pr close)",
    "shell(gh release create)",
    "shell(gh release delete)",
    "shell(gh repo delete)",
)

PROFILES = {
    "observe": Profile(
        description=(
            "Read/review-oriented profile. File writes are denied and high-impact "
            "remote shell actions are denied."
        ),
        deny_tools=("write", *REMOTE_GUARDRAILS),
    ),
    "author": Profile(
        description=(
            "Authoring profile. Writes remain available but are not auto-approved; "
            "high-impact remote shell actions are denied."
        ),
        deny_tools=REMOTE_GUARDRAILS,
    ),
}


def _which(candidates: Sequence[str]) -> str:
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SystemExit(f"Executable not found: {' or '.join(candidates)}")


def _clean_remainder(values: list[str]) -> list[str]:
    if values and values[0] == "--":
        return values[1:]
    return values


def _format_command(argv: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return shlex.join(argv)


def _run(argv: list[str], *, env: dict[str, str] | None, dry_run: bool) -> int:
    print(_format_command(argv))
    if dry_run:
        return 0
    completed = subprocess.run(argv, env=env, check=False)
    return completed.returncode


def _profile_env(profile: Profile, inherit_extra_args: bool) -> dict[str, str]:
    env = os.environ.copy()

    # Spec Kit's Copilot integration otherwise enables --yolo by default for
    # programmatic dispatch. Keep this process-local and explicit.
    env["SPECKIT_COPILOT_ALLOW_ALL_TOOLS"] = "0"

    policy_args = profile.cli_args()
    if inherit_extra_args and env.get("SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS"):
        existing = shlex.split(env["SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS"])
        policy_args = [*existing, *policy_args]

    env["SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS"] = shlex.join(policy_args)
    return env


def command_show(_: argparse.Namespace) -> int:
    print("Copilot repository permission profiles:\n")
    for name, profile in PROFILES.items():
        print(f"{name}: {profile.description}")
        for tool in profile.deny_tools:
            print(f"  deny: {tool}")
        print()
    print("All profiles intentionally avoid --available-tools so agent capability discovery is not artificially capped.")
    print("All profiles intentionally avoid --yolo/--allow-all; permissions not denied remain subject to Copilot's normal approval model.")
    return 0


def command_copilot(args: argparse.Namespace) -> int:
    profile = PROFILES[args.profile]
    executable = _which(("copilot", "copilot.cmd"))
    passthrough = _clean_remainder(args.args)
    argv = [executable, *profile.cli_args(), *passthrough]
    return _run(argv, env=None, dry_run=args.dry_run)


def command_speckit(args: argparse.Namespace) -> int:
    profile = PROFILES[args.profile]
    executable = _which(("specify", "specify.exe"))
    passthrough = _clean_remainder(args.args)
    env = _profile_env(profile, args.inherit_extra_args)

    print("SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0")
    print(
        "SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="
        + env["SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS"]
    )
    return _run([executable, *passthrough], env=env, dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Copilot/Spec Kit using repository-safe Copilot permission profiles."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("show", help="Show effective repository profiles.")
    show.set_defaults(func=command_show)

    copilot = subparsers.add_parser("copilot", help="Launch Copilot CLI with a permission profile.")
    copilot.add_argument("--profile", choices=sorted(PROFILES), default="author")
    copilot.add_argument("--dry-run", action="store_true")
    copilot.add_argument("args", nargs=argparse.REMAINDER)
    copilot.set_defaults(func=command_copilot)

    speckit = subparsers.add_parser(
        "speckit",
        help="Run a specify command with safe environment for any Copilot CLI dispatch it performs.",
    )
    speckit.add_argument("--profile", choices=sorted(PROFILES), default="author")
    speckit.add_argument("--dry-run", action="store_true")
    speckit.add_argument(
        "--inherit-extra-args",
        action="store_true",
        help=(
            "Preserve existing SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS before appending "
            "repository deny rules. Disabled by default for deterministic policy."
        ),
    )
    speckit.add_argument("args", nargs=argparse.REMAINDER)
    speckit.set_defaults(func=command_speckit)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
