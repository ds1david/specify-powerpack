#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

DEFAULT_POWERPACK_REF = "feat/chatgpt-project-provider-no-browser"
DEFAULT_POWERPACK_REPO_URL = "https://github.com/ds1david/speckit-powerpack.git"
DEFAULT_POWERPACK_REPO = Path.home() / "workspace" / "speckit-powerpack"
DEFAULT_EVIDENCE_ROOT = Path.home() / "powerpack-homologation"

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
SKIPPED = "SKIPPED"
WARN = "WARN"


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""


class HarnessError(RuntimeError):
    pass


class Harness:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.project = Path(args.project_path).expanduser().resolve()
        stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        self.root = Path(args.evidence_root).expanduser().resolve() / stamp
        self.root.mkdir(parents=True, exist_ok=False)
        self.scenario = "common"
        self.checks: list[Check] = []

    @property
    def current_dir(self) -> Path:
        path = self.root / self.scenario
        path.mkdir(parents=True, exist_ok=True)
        return path

    def log(self, message: str) -> None:
        print(message, flush=True)

    def record(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name=name, status=status, detail=detail))
        suffix = f" - {detail}" if detail else ""
        self.log(f"[{status:7}] {name}{suffix}")

    def command(
        self,
        cmd: Sequence[str],
        *,
        label: str,
        cwd: Path | None = None,
        expected_codes: Iterable[int] = (0,),
    ) -> subprocess.CompletedProcess[str]:
        target = cwd or self.project
        self.log(f"\n$ {' '.join(cmd)}")
        completed = subprocess.run(
            list(cmd),
            cwd=target,
            text=True,
            capture_output=True,
            shell=False,
        )
        combined = completed.stdout
        if completed.stderr:
            combined += ("\n" if combined else "") + completed.stderr
        (self.current_dir / f"{label}.txt").write_text(combined, encoding="utf-8")
        if combined.strip():
            print(combined.rstrip())
        expected = set(expected_codes)
        if completed.returncode not in expected:
            raise HarnessError(
                f"{label} returned {completed.returncode}; expected {sorted(expected)}"
            )
        return completed

    def preflight(self) -> None:
        self.scenario = "common"
        if not self.project.is_dir():
            raise HarnessError(f"Project directory does not exist: {self.project}")

        scenario = self.args.scenario.upper()
        required = ["git", "uv", "specify"]
        if scenario in {"H1", "H2", "H3", "H4", "ALL"}:
            required.append("codex")
        if scenario in {"H3", "H4", "H5", "ALL"}:
            required.append("copilot")
        missing = [name for name in required if shutil.which(name) is None]
        if missing:
            raise HarnessError("Missing required executable(s): " + ", ".join(missing))

        repo_root = self.command(
            ["git", "rev-parse", "--show-toplevel"],
            label="repository-root",
        ).stdout.strip()
        self.record("git-repository", PASS, repo_root)

        dirty = self.command(
            ["git", "status", "--porcelain"],
            label="repository-dirty-check",
        ).stdout.strip()
        if dirty and self.args.require_clean:
            raise HarnessError("Working tree is not clean and --require-clean was requested")
        self.record(
            "working-tree-before",
            PASS if not dirty else WARN,
            "clean" if not dirty else "dirty; captured as evidence",
        )

        self.capture_environment()
        self.capture_repository("repository-before")

    def capture_environment(self) -> None:
        commands: list[tuple[str, list[str]]] = [
            ("python", [sys.executable, "--version"]),
            ("uv", ["uv", "--version"]),
            ("specify", ["specify", "version"]),
            ("git", ["git", "--version"]),
        ]
        for name in ("node", "codex", "copilot"):
            if shutil.which(name):
                commands.append((name, [name, "--version"]))

        payload = {
            "captured_at": dt.datetime.now().astimezone().isoformat(),
            "system": platform.system(),
            "platform": platform.platform(),
            "release": platform.release(),
            "is_wsl": "microsoft" in platform.release().casefold(),
            "python_executable": sys.executable,
            "project": str(self.project),
            "powerpack_repo": str(Path(self.args.powerpack_repo).expanduser()),
            "powerpack_ref": self.args.powerpack_ref,
            "commands": {},
        }
        text: list[str] = []
        for name, cmd in commands:
            cp = subprocess.run(cmd, text=True, capture_output=True, shell=False)
            output = (cp.stdout + cp.stderr).strip()
            payload["commands"][name] = {
                "returncode": cp.returncode,
                "output": output,
            }
            text.extend([f"=== {name.upper()} ===", output, ""])

        (self.current_dir / "environment.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.current_dir / "environment.txt").write_text(
            "\n".join(text), encoding="utf-8"
        )

    def capture_repository(self, label: str) -> None:
        sections: list[str] = []
        for cmd in (
            ["git", "status"],
            ["git", "branch", "--show-current"],
            ["git", "rev-parse", "HEAD"],
            ["git", "remote", "-v"],
        ):
            cp = subprocess.run(
                cmd,
                cwd=self.project,
                text=True,
                capture_output=True,
                shell=False,
            )
            sections.append(f"$ {' '.join(cmd)}\n{cp.stdout}{cp.stderr}")
        (self.current_dir / f"{label}.txt").write_text(
            "\n".join(sections), encoding="utf-8"
        )

    def install_tool(self) -> None:
        if self.args.skip_tool_install:
            self.record("powerpack-tool-install", SKIPPED, "--skip-tool-install")
            return

        if self.args.install_source == "local":
            source_path = Path(self.args.powerpack_repo).expanduser().resolve()
            if not source_path.is_dir():
                raise HarnessError(f"Local PowerPack repository not found: {source_path}")
            source = str(source_path)
        else:
            source = f"git+{DEFAULT_POWERPACK_REPO_URL}@{self.args.powerpack_ref}"

        self.command(
            ["uv", "tool", "install", "--force", source],
            label="powerpack-tool-install",
        )
        self.record("powerpack-tool-install", PASS, source)
        self.command(
            ["speckit-powerpack", "--version"],
            label="powerpack-version",
        )

    def materialize(self, integration: str) -> None:
        self.command(
            [
                "speckit-powerpack",
                "install",
                str(self.project),
                "--integration",
                integration,
                "--bootstrap-speckit",
                "--no-update-check",
            ],
            label="powerpack-project-install",
        )

    def read_review(self) -> dict:
        path = self.project / ".specify" / "powerpack" / "review.json"
        if not path.is_file():
            raise HarnessError(f"Missing review config: {path}")
        shutil.copy2(path, self.current_dir / "review-config.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def copy_smoke(self, filename: str) -> dict:
        path = self.project / ".specify" / "powerpack" / "smoke" / "code-review.json"
        if not path.is_file():
            raise HarnessError(f"Smoke report missing: {path}")
        target = self.current_dir / filename
        shutil.copy2(path, target)
        return json.loads(target.read_text(encoding="utf-8"))

    def require(self, name: str, condition: bool, detail: str = "") -> None:
        self.record(name, PASS if condition else FAIL, detail)
        if not condition:
            raise HarnessError(f"Assertion failed: {name}{': ' + detail if detail else ''}")

    def assert_cli_smoke(self, report: dict) -> None:
        flow = report.get("flows", {}).get("cli", {})
        response = str(flow.get("response") or "")
        self.require(
            "cli-smoke-ok",
            report.get("ok") is True and flow.get("ok") is True,
        )
        self.require("cli-provider-codex", flow.get("provider") == "codex")
        self.require("cli-project-id-empty", not flow.get("project_id"))
        self.require(
            "cli-marker",
            flow.get("marker") == "POWERPACK_SMOKE_CLI_OK"
            and "POWERPACK_SMOKE_CLI_OK" in response,
        )
        self.require(
            "cli-found-division-by-zero-defect",
            "zero" in response.casefold() or "division" in response.casefold(),
            response,
        )

    def run_h1(self) -> None:
        self.scenario = "H1"
        self.log("\n=== H1: CODEX / NO CHATGPT PROJECT ===")
        self.materialize("codex")
        self.command(
            [
                "speckit-powerpack",
                "review",
                "setup",
                "--path",
                str(self.project),
                "--no-project",
            ],
            label="review-setup-no-project",
        )

        doctor = self.command(
            ["speckit-powerpack", "doctor", str(self.project)],
            label="doctor",
        )
        for token in (
            "OK    specify",
            "OK    spec-kit-project",
            "OK    powerpack-runtime",
            "OK    selected-executor",
            "OK    codex-auth-json",
            "OK    review-provider-configured",
        ):
            self.require(f"doctor:{token.strip()}", token in doctor.stdout)

        review = self.read_review()
        web = review.get("chatgpt_web") if isinstance(review.get("chatgpt_web"), dict) else {}
        self.require("provider-is-codex", review.get("provider") == "codex")
        self.require("project-required-false", web.get("required") is False)
        self.require("project-enabled-false", web.get("enabled") is False)
        self.require("project-mode-disabled", web.get("mode") == "disabled")
        self.require("project-id-empty", not web.get("project_id"))
        self.require("project-url-empty", not web.get("project_url"))

        self.command(
            [
                "speckit-powerpack",
                "review",
                "smoke",
                "--flow",
                "cli",
                "--path",
                str(self.project),
            ],
            label="cli-smoke",
        )
        self.assert_cli_smoke(self.copy_smoke("cli-smoke.json"))

        negative = self.command(
            [
                "speckit-powerpack",
                "review",
                "smoke",
                "--flow",
                "web",
                "--path",
                str(self.project),
            ],
            label="web-negative-smoke",
            expected_codes=range(1, 256),
        )
        negative_report = self.copy_smoke("web-negative-smoke.json")
        web_flow = negative_report.get("flows", {}).get("web", {})
        error = str(web_flow.get("error") or "")
        self.require(
            "web-without-project-fails-closed",
            negative.returncode != 0
            and negative_report.get("ok") is False
            and "not linked to a ChatGPT Project" in error,
            error,
        )
        self.finish_scenario(PASS)

    def run_h2(self) -> None:
        self.scenario = "H2"
        self.log("\n=== H2: CODEX / CHATGPT PROJECT ===")
        if not self.args.chatgpt_project:
            self.record(
                "chatgpt-project-selector",
                BLOCKED,
                "Provide --chatgpt-project or POWERPACK_CHATGPT_PROJECT",
            )
            self.finish_scenario(BLOCKED)
            return

        self.materialize("codex")
        self.command(
            [
                "speckit-powerpack",
                "review",
                "setup",
                "--path",
                str(self.project),
                "--yes-project",
                "--project",
                self.args.chatgpt_project,
            ],
            label="review-setup-project",
        )
        self.command(
            ["speckit-powerpack", "doctor", str(self.project)],
            label="doctor",
        )

        review = self.read_review()
        web = review.get("chatgpt_web") if isinstance(review.get("chatgpt_web"), dict) else {}
        self.require("provider-is-chatgpt-project", review.get("provider") == "chatgpt-project")
        self.require("project-required-true", web.get("required") is True)
        self.require("project-enabled-true", web.get("enabled") is True)
        self.require("project-mode-backend-api", web.get("mode") == "backend-api")
        self.require("project-id-present", bool(web.get("project_id")), str(web.get("project_id") or ""))

        self.command(
            [
                "speckit-powerpack",
                "review",
                "smoke",
                "--flow",
                "both",
                "--path",
                str(self.project),
            ],
            label="both-smoke",
        )
        report = self.copy_smoke("both-smoke.json")
        self.assert_cli_smoke(report)

        web_flow = report.get("flows", {}).get("web", {})
        checks = web_flow.get("checks") if isinstance(web_flow.get("checks"), dict) else {}
        self.require("project-smoke-ok", web_flow.get("ok") is True)
        self.require("project-provider", web_flow.get("provider") == "chatgpt-project")
        self.require("project-response-non-empty", checks.get("response_non_empty") is True)
        self.require("project-name-present", checks.get("project_name_present") is True)
        self.require("project-arithmetic", checks.get("one_plus_one_equals_two") is True)
        self.require("project-max-100-words", checks.get("max_100_words") is True)

        response = str(web_flow.get("response") or "")
        (self.current_dir / "project-response.txt").write_text(
            response + "\n", encoding="utf-8"
        )

        if self.args.confirm_project_mission:
            mission_ok = True
        elif self.args.non_interactive:
            mission_ok = False
        else:
            print("\n=== MANUAL PROJECT MISSION VERIFICATION ===")
            print(response)
            answer = input(
                "A missão retornada corresponde ao ChatGPT Project vinculado? [y/N]: "
            ).strip().casefold()
            mission_ok = answer in {"y", "yes", "s", "sim"}

        self.record(
            "project-mission-semantics",
            PASS if mission_ok else BLOCKED,
            "human-confirmed" if mission_ok else "manual confirmation required",
        )
        self.finish_scenario(PASS if mission_ok else BLOCKED)

    def finish_scenario(self, status: str) -> None:
        self.capture_repository("repository-after")
        payload = {
            "scenario": self.scenario,
            "status": status,
            "project": str(self.project),
            "powerpack_ref": self.args.powerpack_ref,
            "checks": [asdict(check) for check in self.checks],
        }
        (self.current_dir / "result.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        lines = [
            f"SCENARIO: {self.scenario}",
            f"RESULT: {status}",
            "",
            "CHECKS:",
        ]
        lines.extend(
            f"- {check.status}: {check.name}"
            + (f" - {check.detail}" if check.detail else "")
            for check in self.checks
        )
        (self.current_dir / "result.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def write_summary(self) -> None:
        failed = any(check.status == FAIL for check in self.checks)
        blocked = any(check.status == BLOCKED for check in self.checks)
        overall = FAIL if failed else (BLOCKED if blocked else PASS)
        payload = {
            "overall": overall,
            "scenario": self.args.scenario.upper(),
            "project": str(self.project),
            "powerpack_ref": self.args.powerpack_ref,
            "evidence": str(self.root),
            "checks": [asdict(check) for check in self.checks],
        }
        (self.root / "summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("\n============================================")
        print(" SpecKit PowerPack Homologation")
        print("============================================")
        print(f"Scenario: {self.args.scenario.upper()}")
        print(f"Overall:  {overall}")
        print(f"Evidence: {self.root}")
        print("============================================")

    def run(self) -> int:
        try:
            self.preflight()
            self.install_tool()
            scenario = self.args.scenario.upper()
            if scenario == "H1":
                self.run_h1()
            elif scenario == "H2":
                self.run_h2()
            elif scenario in {"H3", "H4", "H5"}:
                self.scenario = scenario
                self.record(
                    "scenario-support",
                    BLOCKED,
                    "Copilot integration is not supported by the browserless baseline yet",
                )
                self.finish_scenario(BLOCKED)
            elif scenario == "ALL":
                raise HarnessError(
                    "Run H1/H2 individually in the WSL-first harness; ALL will be enabled after scenario isolation is finalized"
                )
            else:
                raise HarnessError(f"Unknown scenario: {scenario}")
            self.write_summary()
            return 0 if not any(check.status == FAIL for check in self.checks) else 1
        except (HarnessError, OSError, json.JSONDecodeError) as exc:
            self.record("harness", FAIL, str(exc))
            try:
                self.finish_scenario(FAIL)
                self.write_summary()
            except Exception:
                pass
            print(f"\nHOMOLOGATION FAILED: {exc}", file=sys.stderr)
            print(f"Evidence: {self.root}", file=sys.stderr)
            return 1


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SpecKit PowerPack homologation harness (WSL/Linux first)"
    )
    parser.add_argument(
        "scenario",
        choices=["H1", "H2", "H3", "H4", "H5", "all", "h1", "h2", "h3", "h4", "h5"],
    )
    parser.add_argument(
        "--project-path",
        default=".",
        help="Spec Kit project under homologation; defaults to current directory",
    )
    parser.add_argument("--powerpack-ref", default=DEFAULT_POWERPACK_REF)
    parser.add_argument(
        "--powerpack-repo",
        default=str(DEFAULT_POWERPACK_REPO),
        help="Local PowerPack clone used with --install-source local",
    )
    parser.add_argument(
        "--install-source",
        choices=["remote", "local"],
        default="remote",
    )
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument(
        "--chatgpt-project",
        default=os.environ.get("POWERPACK_CHATGPT_PROJECT"),
        help="ChatGPT Project id, URL or unique name",
    )
    parser.add_argument("--skip-tool-install", action="store_true")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Block when the target repository is dirty before homologation",
    )
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument(
        "--confirm-project-mission",
        action="store_true",
        help="Record H2 mission semantics as already human-verified",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    return Harness(parse_args(argv)).run()


if __name__ == "__main__":
    raise SystemExit(main())
