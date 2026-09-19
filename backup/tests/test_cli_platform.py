from __future__ import annotations

import argparse

from speckit_powerpack import cli


def test_version_parser_and_minimum_contract():
    assert cli.parse_version("0.14.3") == (0, 14, 3)
    assert cli.parse_version("Spec Kit CLI: 1.0.4") == (1, 0, 4)
    assert cli.spec_kit_compatible("0.14.3") is False
    assert cli.spec_kit_compatible("1.0.0") is True
    assert cli.spec_kit_compatible("1.0.4") is True


def test_spec_kit_bootstrap_uses_pinned_git_package_and_force(monkeypatch):
    calls = []
    specify_checks = iter([None, "/usr/bin/specify"])

    def fake_which(name):
        if name == "specify":
            return next(specify_checks)
        if name == "uv":
            return "/usr/bin/uv"
        return None

    monkeypatch.setattr(cli.shutil, "which", fake_which)
    monkeypatch.setattr(cli, "specify_version", lambda binary: "1.0.4")
    monkeypatch.setattr(cli, "run", lambda argv, **kwargs: calls.append(argv))
    assert cli.ensure_specify(bootstrap=True) == "/usr/bin/specify"
    assert calls == [[
        "/usr/bin/uv", "tool", "install", "--force",
        f"git+{cli.SPECKIT_REPO}@{cli.SPECKIT_TESTED_TAG}",
    ]]


def test_incompatible_spec_kit_blocks_without_bootstrap(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/specify" if name == "specify" else None)
    monkeypatch.setattr(cli, "specify_version", lambda binary: "0.14.3")
    try:
        cli.ensure_specify(bootstrap=False)
    except cli.PowerPackError as exc:
        message = str(exc)
        assert "0.14.3" in message
        assert ">= 1.0.0" in message
    else:
        raise AssertionError("incompatible Spec Kit should block")


def _subparser(parser: argparse.ArgumentParser, name: str):
    action = next(item for item in parser._actions if isinstance(item, argparse._SubParsersAction))
    return action.choices[name]


def test_cli_exposes_only_browserless_review_surface():
    parser = cli.build_parser()
    review = _subparser(parser, "review")
    action = next(item for item in review._actions if isinstance(item, argparse._SubParsersAction))
    assert set(action.choices) == {"setup", "status", "project", "run"}
    run_parser = action.choices["run"]
    pr = next(item for item in run_parser._actions if item.dest == "pr")
    assert pr.required is True


def test_review_run_defaults_to_sol_xhigh():
    parser = cli.build_parser()
    args = parser.parse_args(["review", "run", "--pr", "12"])
    assert args.model == "gpt-5.6-sol"
    assert args.effort == "xhigh"
    assert args.timeout == 600
