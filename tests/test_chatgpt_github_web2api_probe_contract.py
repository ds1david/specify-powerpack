from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "homologation" / "web2api_github_driver_probe.py"
ORCHESTRATOR = ROOT / "scripts" / "homologation" / "probe_chatgpt_github_web2api.py"
PS1 = ROOT / "scripts" / "homologation" / "probe_chatgpt_github_web2api.ps1"


def _load_helper():
    spec = importlib.util.spec_from_file_location("web2api_github_driver_probe", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_helper_uses_web2api_driver_and_native_send_and_stream() -> None:
    text = HELPER.read_text(encoding="utf-8")

    assert "from chatgpt_web2api.cdp_driver import CDPDriver" in text
    assert "driver.send_and_stream(" in text
    assert "original_type_message = driver.type_message" in text
    assert "await original_type_message(text)" in text
    assert "await asyncio.wait_for(observer.mention_event.wait()" in text
    assert "driver.click_send" not in text
    assert "urllib.request" not in text
    assert "websockets" not in text


def test_helper_fails_closed_before_upstream_click_send_when_github_not_resolved() -> None:
    text = HELPER.read_text(encoding="utf-8")

    assert 'client_prepare_source") != "context_change"' in text
    assert 'value.startswith("plugin:connector_")' in text
    assert 'partial.casefold().startswith("github ")' in text
    assert "WEB2API_GITHUB_MENTION_NOT_RESOLVED" in text
    assert '"send_clicked": False' in text


def test_helper_chains_web2api_identity_listener_and_requires_native_submit_evidence() -> None:
    module = _load_helper()

    class FakeDriver:
        def __init__(self):
            self._cdp_event_handlers = {}

    driver = FakeDriver()
    observer = module.GitHubNetworkObserver(driver)

    assert observer._connector_hint(["plugin:connector_test"]) is True
    assert observer._connector_hint([]) is False

    text = HELPER.read_text(encoding="utf-8")
    assert "self._previous_request_handler(message)" in text
    assert "top_level_connector_hint" in text
    assert "message_connector_hint" in text
    assert "ecosystemMention" in text
    assert "observer.final_http_status == 200" in text
    assert "POWERPACK_GITHUB_TOOL_OK" in text


def test_windows_launcher_installs_exact_pinned_web2api_and_uses_same_venv_for_helper() -> None:
    text = PS1.read_text(encoding="utf-8")

    assert '497527dceabfa3f95961e23c291e618c5570f1ac' in text
    assert "Octo-Lex/ChatGPT-Web2API/archive/$Web2ApiRevision.zip" in text
    assert '"-m", "chatgpt_web2api", "start"' in text
    assert "--user-data-dir" in text
    assert "$servicePython @helperArgs" in text
    assert "web2api_github_driver_probe" not in text  # path is injected, not duplicated logic


def test_orchestrator_keeps_codex_auth_as_preflight_only() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")

    assert "ChatGPTBackendClient" in text
    assert "_resolve_connector(client)" in text
    assert '"role": "preflight-only"' in text
    assert "connector_id_exposed" in text
    assert "powershell.exe" in text
    assert "probe_chatgpt_github_web2api.ps1" in text
    assert "Authorization" not in text
    assert "Cookie" not in text


def test_direct_cdp_probe_is_not_the_resumed_web2api_entrypoint() -> None:
    orchestrator = ORCHESTRATOR.read_text(encoding="utf-8")
    ps1 = PS1.read_text(encoding="utf-8")

    assert "probe_chatgpt_github_cdp.ps1" not in orchestrator
    assert "probe_chatgpt_github_cdp.ps1" not in ps1
    assert "probe_chatgpt_github_cdp_compat.ps1" not in orchestrator
