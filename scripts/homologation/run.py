#!/usr/bin/env python3
from __future__ import annotations

import sys

from homologate import BLOCKED, FAIL, PASS, Harness, HarnessError, parse_args


class BindingAwareHarness(Harness):
    """WSL-first harness with an explicit fail-fast ChatGPT Project bind gate."""

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
