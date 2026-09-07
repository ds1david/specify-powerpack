from __future__ import annotations

from . import cli as core
from .backend_compat import install_backend_compat
from .chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError


# The browserless architecture intentionally prevents install/update/init from
# pulling Playwright or Chromium. Review setup chooses CodexProvider or the
# direct ChatGPTProjectProvider instead.
core.ensure_playwright_browser = lambda: None
core.enforce_mandatory_web_review = lambda review_path: None

# Install the ChatGPT backend compatibility layer before importing/building the
# review CLI. This replaces the browser-oriented /me auth probe with the
# account-scoped Codex /wham/usage probe and applies Codex-compatible headers.
install_backend_compat()

from . import cli_project_provider as provider_cli  # noqa: E402


def _live_auth_ready() -> bool:
    """Doctor readiness must prove backend access, not merely auth.json presence."""
    try:
        ChatGPTBackendClient().validate_auth()
        return True
    except ChatGPTProjectError:
        return False


provider_cli._auth_ready = _live_auth_ready
main = provider_cli.main
