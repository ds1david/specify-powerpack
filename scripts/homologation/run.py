#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from homologate import BLOCKED, FAIL, PASS, Harness, HarnessError, parse_args


COPILOT_REVIEW_1_MARKER = "POWERPACK_COPILOT_REVIEW_1_OK"
COPILOT_REVIEW_2_MARKER = "POWERPACK_COPILOT_REVIEW_2_OK"


class BindingAwareHarness(Harness):
    """WSL-first homologation harness with fail-fast bindings and clean config starts."""

    def capture_environment(self) -> None:
        """Capture environment without touching Codex in Copilot-only H5."""
        if self.args.scenario.upper() != "H5":
            super().capture_environment()
            return

        commands: list[tuple[str, list[str]]] = [
            ("python", [sys.executable, "--version"]),
            ("uv", ["uv", "--version"]),
            ("specify", ["specify", "version"]),
            ("git", ["git", "--version"]),
        ]
        for name in ("node", "copilot"):
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
            "scenario_isolation": {
                "codex_invoked": False,
                "chatgpt_project_used": False,
                "reviewer": "copilot",
            },
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

    def materialize(self, integration: str) -> None:
        """Install managed assets, then overwrite stale PowerPack project config."""
        super().materialize(integration)
        self.command(
            [
                "speckit-powerpack",
                "update",
                str(self.project),
                "--project-only",
                "--force",
                "--yes",
                "--reset-config",
                "--integration",
                integration,
                "--bootstrap-speckit",
            ],
            label="powerpack-config-reset",
        )
        self.record(
            "powerpack-config-reset",
            PASS,
            "managed project configuration overwritten before scenario setup",
        )

        review = self.read_review()
        web = review.get("chatgpt_web") if isinstance(review.get("chatgpt_web"), dict) else {}
        stale_fields = {
            "project_alias": web.get("project_alias"),
            "project_id": web.get("project_id"),
            "project_name": web.get("project_name"),
            "project_url": web.get("project_url"),
            "account_label": web.get("account_label"),
            "authorization": web.get("authorization"),
        }
        stale = {key: value for key, value in stale_fields.items() if value not in (None, "")}
        if stale:
            self.record("powerpack-config-reset-state", FAIL, json.dumps(stale, ensure_ascii=False))
            raise HarnessError(
                "PowerPack configuration reset left stale Project binding fields; scenario stopped"
            )
        self.record("powerpack-config-reset-state", PASS, "no stale ChatGPT Project binding")

    def bind_chatgpt_project(self) -> dict:
        selector = str(self.args.chatgpt_project or "").strip()
        if not selector:
            self.record(
                "chatgpt-project-bind",
                BLOCKED,
                "Provide --chatgpt-project or POWERPACK_CHATGPT_PROJECT",
            )
            raise HarnessError("ChatGPT Project bind requires an explicit project selector")

        result = self.command(
            [
                "speckit-powerpack",
                "review",
                "setup",
                "--path",
                str(self.project),
                "--yes-project",
                "--project",
                selector,
            ],
            label="project-bind",
            expected_codes=range(0, 256),
        )

        if result.returncode != 0:
            self.record(
                "chatgpt-project-bind",
                FAIL,
                f"exit={result.returncode}; see project-bind.txt",
            )
            raise HarnessError(
                "ChatGPT Project bind failed; H2 stopped before doctor and smoke tests"
            )

        self.record("chatgpt-project-bind", PASS, "command completed")

        review = self.read_review()
        web = review.get("chatgpt_web") if isinstance(review.get("chatgpt_web"), dict) else {}
        checks = {
            "provider": review.get("provider") == "chatgpt-project",
            "required": web.get("required") is True,
            "enabled": web.get("enabled") is True,
            "mode": web.get("mode") == "backend-api",
            "project_id": bool(web.get("project_id")),
            "project_url": bool(web.get("project_url")),
        }
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            self.record(
                "chatgpt-project-bind-state",
                FAIL,
                "invalid post-bind state: " + ", ".join(failed),
            )
            raise HarnessError(
                "ChatGPT Project bind did not persist a valid provider state; H2 stopped before doctor and smoke tests"
            )

        self.record(
            "chatgpt-project-bind-state",
            PASS,
            f"project_id={web.get('project_id')}",
        )
        return review

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

        # Binding is a first-class gate. Any command or persisted-state failure
        # raises immediately, so doctor/smokes are never executed after a bad bind.
        self.bind_chatgpt_project()

        self.command(
            [
                "speckit-powerpack",
                "doctor",
                str(self.project),
                "--strict-review",
            ],
            label="doctor-after-bind",
        )
        self.record("post-bind-doctor", PASS, "strict review readiness passed")

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

    def resolve_current_spec(self) -> tuple[str, Path]:
        branch = self.command(
            ["git", "branch", "--show-current"],
            label="copilot-current-branch",
        ).stdout.strip()
        if not branch:
            raise HarnessError("Copilot-only review requires a named Git branch")

        specs_root = self.project / "specs"
        if not specs_root.is_dir():
            raise HarnessError(f"Spec Kit specs directory not found: {specs_root}")

        names: list[str] = []
        for candidate in (branch, branch.removeprefix("spec/"), branch.rsplit("/", 1)[-1]):
            if candidate and candidate not in names:
                names.append(candidate)

        matches: list[Path] = []
        for name in names:
            candidate = specs_root / name
            if (candidate / "spec.md").is_file() and candidate not in matches:
                matches.append(candidate)

        if not matches:
            tail = branch.rsplit("/", 1)[-1]
            for candidate in sorted(specs_root.iterdir()):
                if not candidate.is_dir() or not (candidate / "spec.md").is_file():
                    continue
                if candidate.name == tail or candidate.name.endswith(tail) or branch.endswith(candidate.name):
                    matches.append(candidate)

        if len(matches) != 1:
            detail = ", ".join(path.name for path in matches) or "none"
            raise HarnessError(
                f"Could not resolve exactly one current SPEC for branch '{branch}'. Matches: {detail}"
            )

        self.record("copilot-branch-spec-binding", PASS, f"{branch} -> {matches[0].name}")
        return branch, matches[0]

    def _copilot_review(self, *, number: int, branch: str, spec_dir: Path, marker: str) -> str:
        relative_spec = spec_dir.relative_to(self.project).as_posix()
        focus = (
            "correctness, SPEC compliance, behavioral regressions, tests and security"
            if number == 1
            else "fresh adversarial review: concurrency, failure paths, boundaries, idempotency, composition root and vacuously green tests"
        )
        prompt = f"""/review the changes on the current branch as a read-only code review.

POWERPACK HOMOLOGATION CONTEXT
review_mode: copilot-only-local
branch: {branch}
spec: {relative_spec}
pull_request: NOT_REQUIRED
review_round: {number}

Review only the implementation belonging to this current Spec Kit SPEC and branch.
Use repository files, the SPEC artifacts and Git diff/history as evidence.
Do not edit files, do not commit, do not push, do not use URLs, and do not delegate to Codex or ChatGPT.
Focus on {focus}.
For round 2, do not inherit the verdict from round 1; independently challenge the current snapshot.
Return concrete findings with file/evidence when present. If no blocking finding remains, say so explicitly.
Finish with this exact marker on its own line:
{marker}
"""
        allow_tools = (
            "read,"
            "shell(git status),shell(git branch),shell(git diff),shell(git show),"
            "shell(git rev-parse),shell(git merge-base),shell(git log)"
        )
        deny_tools = (
            "write,memory,url,"
            "shell(git push),shell(git commit),shell(git reset),shell(git checkout),"
            "shell(git switch),shell(git clean),shell(git restore),shell(git merge),"
            "shell(git rebase),shell(git cherry-pick)"
        )
        result = self.command(
            [
                "copilot",
                "-p",
                prompt,
                "-s",
                "--no-ask-user",
                f"--allow-tool={allow_tools}",
                f"--deny-tool={deny_tools}",
            ],
            label=f"copilot-review-{number}",
        )
        response = result.stdout.strip()
        self.require(f"copilot-review-{number}-response", bool(response), "non-empty response required")
        self.require(f"copilot-review-{number}-marker", marker in response, marker)
        (self.current_dir / f"copilot-review-{number}-response.txt").write_text(
            response + "\n", encoding="utf-8"
        )
        return response

    def run_h5(self) -> None:
        self.scenario = "H5"
        self.log("\n=== H5: COPILOT ONLY / TWO LOCAL CODE REVIEWS ===")

        # H5 intentionally does not configure Codex or ChatGPT. It validates the
        # isolated Copilot reviewer path against the current SPEC + branch.
        branch, spec_dir = self.resolve_current_spec()
        head_before = self.command(["git", "rev-parse", "HEAD"], label="copilot-head-before").stdout.strip()
        status_before = self.command(["git", "status", "--porcelain"], label="copilot-status-before").stdout

        self.record("copilot-only-no-codex-setup", PASS, "harness does not invoke Codex")
        self.record("copilot-only-no-chatgpt-setup", PASS, "no ChatGPT Project bind or Web provider")

        self._copilot_review(
            number=1,
            branch=branch,
            spec_dir=spec_dir,
            marker=COPILOT_REVIEW_1_MARKER,
        )
        self._copilot_review(
            number=2,
            branch=branch,
            spec_dir=spec_dir,
            marker=COPILOT_REVIEW_2_MARKER,
        )

        head_after = self.command(["git", "rev-parse", "HEAD"], label="copilot-head-after").stdout.strip()
        status_after = self.command(["git", "status", "--porcelain"], label="copilot-status-after").stdout
        self.require("copilot-read-only-head", head_before == head_after, f"{head_before} -> {head_after}")
        self.require("copilot-read-only-working-tree", status_before == status_after)
        self.finish_scenario(PASS)

    def run(self) -> int:
        try:
            self.preflight()
            self.install_tool()
            scenario = self.args.scenario.upper()
            if scenario == "H1":
                self.run_h1()
            elif scenario == "H2":
                self.run_h2()
            elif scenario in {"H3", "H4"}:
                self.scenario = scenario
                self.record(
                    "scenario-support",
                    BLOCKED,
                    "mixed Copilot/Codex provider integration is not implemented by the browserless baseline yet",
                )
                self.finish_scenario(BLOCKED)
            elif scenario == "H5":
                self.run_h5()
            elif scenario == "ALL":
                raise HarnessError(
                    "Run scenarios individually in the WSL-first harness so each starts from isolated evidence/configuration"
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


def main() -> int:
    harness = BindingAwareHarness(parse_args())
    result = harness.run()
    if result != 0 or any(check.status == FAIL for check in harness.checks):
        return 1
    if any(check.status == BLOCKED for check in harness.checks):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
