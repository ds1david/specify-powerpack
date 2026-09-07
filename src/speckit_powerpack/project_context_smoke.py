from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


PROJECT_CONTEXT_SMOKE_PROMPT = (
    "me diga qual é o nome do projeto e sua principal missão, produza uma resposta "
    "simplificada de no máximo 100 palavras. e me responda quanto é 1 +1"
)


def install_project_context_smoke(provider_cli) -> None:
    """Replace only the Web/Project smoke with a context-verification smoke.

    The CLI smoke remains the independent code-review transport smoke. The Web
    smoke intentionally asks a simple question whose answer lets a human verify
    that ChatGPT Project context was actually loaded.
    """

    original_smoke_prompt = provider_cli._smoke_prompt
    run_codex_cli_review = provider_cli.run_codex_cli_review
    run_project_review = provider_cli.run_project_review
    project_target = provider_cli._project_target
    configured_binding = provider_cli._configured_binding
    powerpack_error = provider_cli.core.PowerPackError

    def cmd_review_smoke(args) -> None:
        project = Path(args.path).resolve()
        flows = [args.flow] if args.flow != "both" else ["cli", "web"]
        report: dict[str, Any] = {"ok": True, "flows": {}}

        for flow in flows:
            marker = "POWERPACK_SMOKE_CLI_OK" if flow == "cli" else None
            try:
                if flow == "cli":
                    result = run_codex_cli_review(
                        prompt=original_smoke_prompt(marker),
                        cwd=project,
                        timeout=args.timeout,
                    )
                    ok = marker in result.text and (
                        "zero" in result.text.casefold() or "division" in result.text.casefold()
                    )
                    flow_report = {
                        "ok": bool(ok),
                        "provider": result.provider,
                        "project_id": result.project_id,
                        "response_id": result.response_id,
                        "marker": marker,
                        "response": result.text,
                    }
                else:
                    binding = configured_binding(project) or {}
                    expected_project_name = str(binding.get("project_name") or "").strip()
                    result = run_project_review(
                        prompt=PROJECT_CONTEXT_SMOKE_PROMPT,
                        project_id_or_url=project_target(project, args.project),
                        model=args.model,
                        effort=args.effort,
                        max_conversations=min(args.max_conversations, 2),
                    )
                    response = result.text.strip()
                    word_count = len(re.findall(r"\S+", response))
                    arithmetic_ok = bool(re.search(r"(?<!\d)2(?!\d)", response))
                    project_name_ok = bool(
                        expected_project_name
                        and expected_project_name.casefold() in response.casefold()
                    )
                    length_ok = 0 < word_count <= 100
                    ok = bool(response) and arithmetic_ok and project_name_ok and length_ok
                    flow_report = {
                        "ok": ok,
                        "provider": result.provider,
                        "project_id": result.project_id,
                        "project_name": result.project_name,
                        "response_id": result.response_id,
                        "prompt": PROJECT_CONTEXT_SMOKE_PROMPT,
                        "checks": {
                            "response_non_empty": bool(response),
                            "project_name_present": project_name_ok,
                            "one_plus_one_equals_two": arithmetic_ok,
                            "max_100_words": length_ok,
                            "word_count": word_count,
                            "mission_semantics": "MANUAL_VERIFY_IN_RESPONSE",
                        },
                        "response": response,
                    }

                    print("\n=== CHATGPT PROJECT CONTEXT SMOKE RESPONSE ===")
                    print(response)
                    print("=== END CHATGPT PROJECT CONTEXT SMOKE RESPONSE ===\n")

                report["flows"][flow] = flow_report
                if not flow_report["ok"]:
                    report["ok"] = False
            except Exception as exc:
                report["ok"] = False
                report["flows"][flow] = {
                    "ok": False,
                    "error": str(exc),
                    "prompt": PROJECT_CONTEXT_SMOKE_PROMPT if flow == "web" else None,
                    "marker": marker,
                }

        smoke_dir = project / ".specify" / "powerpack" / "smoke"
        smoke_dir.mkdir(parents=True, exist_ok=True)
        report_path = smoke_dir / "code-review.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["ok"]:
            raise powerpack_error(f"Code-review smoke failed. See {report_path}")

    provider_cli.cmd_review_smoke = cmd_review_smoke
