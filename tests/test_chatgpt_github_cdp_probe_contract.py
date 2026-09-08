from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
PS1 = ROOT / "scripts" / "homologation" / "probe_chatgpt_github_cdp.ps1"
SH = ROOT / "scripts" / "homologation" / "probe_chatgpt_github_cdp.sh"


def test_cdp_probe_uses_native_frontend_and_fails_closed_before_send() -> None:
    text = PS1.read_text(encoding="utf-8")

    assert '"Network.enable"' in text
    assert '"Input.insertText"' in text
    assert '"/backend-api/f/conversation/prepare' in text
    assert 'client_prepare_source' in text
    assert '"context_change"' in text
    assert '"^plugin:connector_"' in text
    assert 'CDP_GITHUB_MENTION_NOT_RESOLVED' in text
    assert 'Send will NOT be clicked' in text


def test_cdp_probe_requires_connector_metadata_and_native_submit_200() -> None:
    text = PS1.read_text(encoding="utf-8")

    assert 'top_level_connector_hint' in text
    assert 'message_connector_hint' in text
    assert 'ecosystem_mention_present' in text
    assert 'final_http_status' in text
    assert '$finalStatus -eq 200' in text
    assert 'CDP_GITHUB_FLOW_ACCEPTED' in text
    assert 'POWERPACK_GITHUB_TOOL_OK' in text


def test_cdp_probe_does_not_reconstruct_private_backend_submit() -> None:
    text = PS1.read_text(encoding="utf-8")

    assert 'direct_backend_submit_used = $false' in text
    assert 'sentinel_or_proof_fabricated = $false' in text
    assert 'network_headers_logged = $false' in text
    assert 'Invoke-WebRequest' not in text
    assert 'Invoke-RestMethod' in text  # CDP HTTP discovery only.


def test_wsl_launcher_executes_windows_powershell_probe() -> None:
    text = SH.read_text(encoding="utf-8")

    assert 'powershell.exe' in text
    assert 'wslpath -w' in text
    assert 'probe_chatgpt_github_cdp.ps1' in text
    assert '-ExecutionPolicy Bypass' in text
