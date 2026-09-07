from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from speckit_powerpack import cli_project_provider as cli
from speckit_powerpack.chatgpt_project_provider import ReviewResult


def _project(tmp_path: Path) -> Path:
    review = tmp_path / ".specify" / "powerpack" / "review.json"
    review.parent.mkdir(parents=True)
    review.write_text(
        json.dumps(
            {
                "provider": "chatgpt-project",
                "chatgpt_web": {
                    "required": True,
                    "enabled": True,
                    "authorization": "codex-backend-api",
                    "project_id": "g-p-test123",
                    "project_name": "Smoke Project",
                    "project_alias": "smoke",
                    "project_url": "https://chatgpt.com/g/g-p-test123/project",
                },
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_smoke_both_routes_are_independent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = _project(tmp_path)
    calls: list[str] = []

    def fake_cli(**kwargs):
        calls.append("cli")
        return ReviewResult(
            provider="codex",
            text="Division by zero risk.\nPOWERPACK_SMOKE_CLI_OK",
        )

    def fake_web(**kwargs):
        calls.append("web")
        assert kwargs["project_id_or_url"] == "g-p-test123"
        return ReviewResult(
            provider="chatgpt-project",
            project_id="g-p-test123",
            project_name="Smoke Project",
            response_id="resp-test",
            text="Potential division by zero.\nPOWERPACK_SMOKE_WEB_OK",
        )

    monkeypatch.setattr(cli, "run_codex_cli_review", fake_cli)
    monkeypatch.setattr(cli, "run_project_review", fake_web)

    args = argparse.Namespace(
        flow="both",
        path=str(project),
        project=None,
        model="gpt-5.6-sol",
        effort="high",
        max_conversations=2,
        timeout=30,
    )
    cli.cmd_review_smoke(args)

    assert calls == ["cli", "web"]
    report = json.loads((project / ".specify" / "powerpack" / "smoke" / "code-review.json").read_text())
    assert report["ok"] is True
    assert report["flows"]["cli"]["ok"] is True
    assert report["flows"]["web"]["ok"] is True
    assert report["flows"]["web"]["project_id"] == "g-p-test123"


def test_web_smoke_fails_without_project_binding(tmp_path: Path) -> None:
    review = tmp_path / ".specify" / "powerpack" / "review.json"
    review.parent.mkdir(parents=True)
    review.write_text(json.dumps({"provider": "codex", "chatgpt_web": {"required": False}}), encoding="utf-8")

    args = argparse.Namespace(
        flow="web",
        path=str(tmp_path),
        project=None,
        model="gpt-5.6-sol",
        effort="high",
        max_conversations=2,
        timeout=30,
    )

    with pytest.raises(Exception, match="Code-review smoke failed"):
        cli.cmd_review_smoke(args)
