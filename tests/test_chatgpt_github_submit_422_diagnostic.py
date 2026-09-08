from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "homologation" / "diagnose_chatgpt_github_submit_422.py"
SPEC = importlib.util.spec_from_file_location("diagnose_chatgpt_github_submit_422", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_safe_validation_diagnostic_keeps_only_type_loc_and_msg() -> None:
    raw = """{
      "detail": [
        {
          "type": "missing",
          "loc": ["body", "messages", 0, "create_time"],
          "msg": "Field required",
          "input": {
            "system_hints": ["plugin:connector_supersecret"],
            "conduit_token": "must-not-leak"
          }
        }
      ]
    }"""

    report = MODULE.safe_validation_diagnostic(raw)

    assert report == {
        "json": True,
        "body_exposed": False,
        "top_level_keys": ["detail"],
        "validation_errors": [
            {
                "type": "missing",
                "loc": ["body", "messages", 0, "create_time"],
                "msg": "Field required",
            }
        ],
    }
    rendered = str(report)
    assert "connector_supersecret" not in rendered
    assert "must-not-leak" not in rendered
    assert "input" not in rendered


def test_safe_validation_diagnostic_redacts_ids_from_messages() -> None:
    raw = """{
      "error": {
        "type": "validation_error",
        "code": "bad_connector",
        "message": "connector_deadbeef rejected for 123e4567-e89b-12d3-a456-426614174000"
      }
    }"""

    report = MODULE.safe_validation_diagnostic(raw)

    assert report["error"]["type"] == "validation_error"
    assert report["error"]["code"] == "bad_connector"
    assert "connector_deadbeef" not in report["error"]["message"]
    assert "123e4567-e89b-12d3-a456-426614174000" not in report["error"]["message"]
    assert "<redacted>" in report["error"]["message"]


def test_non_json_error_body_is_never_echoed() -> None:
    report = MODULE.safe_validation_diagnostic("private backend diagnostic with token abc123")

    assert report == {
        "json": False,
        "body_exposed": False,
        "validation_errors": [],
    }
    assert "private backend" not in str(report)
