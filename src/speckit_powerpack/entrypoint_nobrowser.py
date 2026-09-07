from __future__ import annotations

from . import cli as core


# The browserless architecture intentionally prevents install/update/init from
# pulling Playwright or Chromium. Review setup chooses CodexProvider or the
# direct ChatGPTProjectProvider instead.
core.ensure_playwright_browser = lambda: None
core.enforce_mandatory_web_review = lambda review_path: None

from .cli_project_provider import main  # noqa: E402,F401
