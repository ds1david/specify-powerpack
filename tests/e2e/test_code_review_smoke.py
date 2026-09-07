from __future__ import annotations

import os
from pathlib import Path

import pytest

from speckit_powerpack.chatgpt_project_provider import run_codex_cli_review, run_project_review


pytestmark = pytest.mark.e2e

RUN_E2E = os.environ.get("POWERPACK_RUN_E2E") == "1"
PROJECT = os.environ.get("POWERPACK_CHATGPT_PROJECT")


def _prompt(marker: str) -> str:
    return f"""Perform a minimal read-only code review of this snippet:

```python
def ratio(total, count):
    return total / count
```

Identify the concrete correctness risk. Finish with exactly:
{marker}
"""


@pytest.mark.skipif(not RUN_E2E, reason="set POWERPACK_RUN_E2E=1 to call the authenticated Codex account")
def test_cli_code_review_smoke() -> None:
    marker = "POWERPACK_SMOKE_CLI_OK"
    result = run_codex_cli_review(prompt=_prompt(marker), cwd=Path.cwd(), timeout=300)
    assert marker in result.text
    assert "zero" in result.text.casefold() or "division" in result.text.casefold()


@pytest.mark.skipif(
    not RUN_E2E or not PROJECT,
    reason="set POWERPACK_RUN_E2E=1 and POWERPACK_CHATGPT_PROJECT=<g-p-id-or-project-url>",
)
def test_web_project_code_review_smoke() -> None:
    marker = "POWERPACK_SMOKE_WEB_OK"
    result = run_project_review(
        prompt=_prompt(marker),
        project_id_or_url=PROJECT,
        model=os.environ.get("POWERPACK_SMOKE_MODEL", "gpt-5.6-sol"),
        effort=os.environ.get("POWERPACK_SMOKE_EFFORT", "high"),
        max_conversations=2,
    )
    assert result.project_id
    assert marker in result.text
    assert "zero" in result.text.casefold() or "division" in result.text.casefold()
