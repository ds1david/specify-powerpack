#!/usr/bin/env python3
"""Experimental Edge/CDP ChatGPT-Web probe (NOT part of the supported provider).

This is a research/homologation probe, a sibling of
``probe_browserless_prompts.py`` and ``smoke_chatgpt_github_browserless.py``. It
adds a NEW transport alongside the existing ones — it removes nothing.

    WHY IT IS SEPARATE / EXPERIMENTAL
    ---------------------------------
    ``docs/DECISIONS_AND_TRADEOFFS.md`` §2 keeps Chrome / CDP / browser-profile
    bridges OUT of the supported browserless provider, and SPEC-001 FR-020 scopes
    the shipped path to the Codex/backend transports. So this lives in
    ``scripts/homologation/`` as "research evidence, not a production
    dependency". Promoting a browser-driven review to a supported capability
    needs a new spec.

    WHAT IT DOES
    ------------
    Drives your REAL, already-authenticated ChatGPT Web session inside a real
    ChatGPT Project conversation — which is the one thing the backend/Responses
    transports cannot do (Decision §4 cost: "the generated review turn is not
    itself a native ChatGPT Project conversation"). It asks the same 3 questions
    as ``probe_browserless_prompts.py`` so the two transports can be compared.

    ARCHITECTURE  (Windows 11 + WSL; no WSL<->Windows port bridging needed)
    ---------------------------------------------------------------------
        WSL2                              Windows
        ----                              -------
        this script ─spawn▶ powershell.exe -Command "npx.cmd chrome-devtools-mcp …"
             │  MCP (JSON-RPC, stdio)          │  --browserUrl / --wsEndpoint
             │                                 │  CDP (same machine → 127.0.0.1)
             ▼                                 ▼
        report JSON                    Edge (signed in to ChatGPT via Google)
                                          └─ Project ▸ conversation ▸ turns 1..3

    The MCP server runs ON WINDOWS and connects to Edge over local 127.0.0.1,
    so there is no 9222 reachability problem from WSL. This script only speaks
    MCP over the subprocess's stdin/stdout.

    ONE-TIME SETUP
    --------------
    1. Node/npm ON WINDOWS (not just WSL):  powershell -Command "npx.cmd --version"
    2. A debuggable Edge signed in to ChatGPT. Pick one:
       a) YOUR normal Edge — quit it fully, relaunch once with:
            msedge.exe --remote-debugging-port=9222 --remote-allow-origins=*
          (reuses your real profile → already signed in; but the agent then
           sees every tab — see SECURITY).
       b) A DEDICATED profile — pass ``--launch``; the probe runs
          edge_chatgpt_launch.ps1, which opens a separate Edge on a free port
          with the right flags. Sign in to ChatGPT once in that window.
       If your Edge already exposes a debug port, the probe auto-discovers it
       (HTTP probe on --port, then the DevToolsActivePort file) — no flags.
    3. First CDP attach, Edge shows "Permitir depuração remota? / Allow remote
       debugging?" — this modal BLOCKS every CDP command until you answer. Click
       "Desativar nas configurações / Turn off in settings" ONCE (persists per
       profile) so it never asks again, then re-run. Clicking "Permitir / Allow"
       also works but only for that session.

    RUN
    ---
        # discover an already-debuggable Edge and drive it:
        python3 scripts/homologation/probe_edge_chatgpt_cdp.py \\
            --project https://chatgpt.com/g/g-p-6a9ba1a060208191a5b6e03a3950b183-specify-powerpack \\
            --pr 15
        # first CDP call hangs / 403 → Edge lacks --remote-allow-origins=*:
        …  --relaunch-my-edge     # closes Edge, reopens YOUR profile debuggable
        …  --launch               # or: dedicated profile (sign in once)
        …  --verbose              # chrome-devtools-mcp DEBUG logs on failure
        # force a specific endpoint instead of discovery:
        …  --ws-endpoint ws://localhost:9222/devtools/browser/<id>
        …  --debug-url http://localhost:9222

    SECURITY: the MCP client can read/modify anything in the attached browser.
    Attaching to your everyday Edge exposes all tabs, cookies and signed-in
    accounts to the agent. A dedicated profile (``--launch``) is safer; use your
    main profile only knowingly.

    BRITTLENESS: this scrapes the ChatGPT Web DOM. Selectors drift; override
    them with ``--sel-*`` flags and inspect ``*-snapshot.txt`` on failure.
    Q2/Q3 drive the REAL ``@`` autocomplete (types ``@``, waits for
    ``--sel-mention-popup``, clicks the entry in ``--sel-mention-item`` whose
    text contains "GitHub") so ChatGPT's own frontend resolves the connector —
    this script never hardcodes a connector id. The popup/item selectors are
    best-guess ARIA roles (``[role=listbox]`` / ``[role=option]``); override them
    if they never match. Each turn's result carries ``mention_engaged``: true
    means the picker was found and clicked, false means it silently fell back to
    literal ``@GitHub`` text (report it, don't trust a false answer as connector
    evidence). The probe still captures no tool-call evidence from the DOM;
    trust a GitHub answer only if it visibly cites tool use.
    (``--no-mention-github`` disables the whole mechanism.)

WARNING: this spends ChatGPT plan usage (a real Web conversation turn).
"""
from __future__ import annotations

import argparse
import base64
from collections import deque
import json
from pathlib import Path
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "specs" / "001-single-skill-baseline" / "T025-evidence"
LAUNCHER = Path(__file__).with_name("edge_chatgpt_launch.ps1")


def _log(msg: str) -> None:
    print(f"  [edge-cdp] {msg}", file=sys.stderr, flush=True)


def _is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text("utf-8", "ignore").lower()
    except OSError:
        return False


def _launcher_command(launcher_args: list[str]) -> list[str]:
    """Run edge_chatgpt_launch.ps1 via -EncodedCommand (UTF-16LE base64) instead
    of `-File \\\\wsl.localhost\\…`. Windows PowerShell reads a BOM-less UTF-8
    .ps1 from a UNC path in the system codepage and chokes on any non-ASCII byte;
    embedding the text in a here-string scriptblock sidesteps file encoding, the
    UNC path, and ExecutionPolicy entirely."""
    script = LAUNCHER.read_text(encoding="utf-8")
    quoted = " ".join(a if a.startswith("-") else "'" + a.replace("'", "''") + "'"
                      for a in launcher_args)
    wrapper = (f"$ErrorActionPreference='Continue'\n"
               f"$__sb = [scriptblock]::Create(@'\n{script}\n'@)\n"
               f"& $__sb {quoted}\n")
    b64 = base64.b64encode(wrapper.encode("utf-16-le")).decode("ascii")
    return ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
            "-OutputFormat", "Text", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64]


_CLIXML_RE = re.compile(r"^(#< CLIXML|<Objs |</Objs>|<Obj )")


def _clean_ps(text: str) -> str:
    """Drop PowerShell's CLIXML stderr framing / progress spam."""
    return "\n".join(ln for ln in text.splitlines()
                     if ln.strip() and not _CLIXML_RE.match(ln.strip())
                     and "Preparando" not in ln and "Preparing modules" not in ln)


# --------------------------------------------------------------------------- #
# Minimal MCP stdio client (JSON-RPC 2.0, newline-delimited).
# --------------------------------------------------------------------------- #
class MCPError(RuntimeError):
    pass


class MCPStdioClient:
    def __init__(self, command: list[str]) -> None:
        self._cmd = command
        self._id = 0
        _log("MCP server: " + " ".join(command))
        self._proc = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            bufsize=1,
        )
        # Reader threads: stdout lines land in a queue (so timeouts are REAL —
        # `readline()` blocks forever with no data and would never honour a
        # deadline); stderr is drained to a bounded tail for diagnostics (a full
        # pipe buffer would deadlock the child mid-run).
        self._out: queue.Queue[str | None] = queue.Queue()
        self._stderr_tail: deque[str] = deque(maxlen=800)
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

    def _pump_stdout(self) -> None:
        if self._proc.stdout is not None:
            for line in self._proc.stdout:
                self._out.put(line.rstrip("\n"))
        self._out.put(None)  # EOF sentinel

    def _pump_stderr(self) -> None:
        if self._proc.stderr is not None:
            for line in self._proc.stderr:
                self._stderr_tail.append(line.rstrip("\n"))

    def _stderr_text(self) -> str:
        return "\n".join(self._stderr_tail)

    def _send(self, obj: dict) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _read_message(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError(f"timed out after {timeout:.0f}s waiting for an MCP message.\n"
                               f"stderr tail:\n{self._stderr_text()[-1800:]}")
            try:
                line = self._out.get(timeout=min(remaining, 5.0))
            except queue.Empty:
                if self._proc.poll() is not None:
                    raise MCPError(f"MCP server exited ({self._proc.returncode}).\n"
                                   f"stderr tail:\n{self._stderr_text()[-2000:]}") from None
                continue
            if line is None:
                raise MCPError(f"MCP server closed stdout ({self._proc.poll()}).\n"
                               f"stderr tail:\n{self._stderr_text()[-2000:]}")
            line = line.strip().lstrip("﻿")
            if not line.startswith("{"):
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    def _request(self, method: str, params: dict, timeout: float = 60.0) -> dict:
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            msg = self._read_message(timeout)
            if msg.get("id") != rid:
                continue  # a notification / log / other id
            if "error" in msg:
                raise MCPError(f"{method}: {msg['error']}")
            return msg.get("result", {})

    def initialize(self) -> dict:
        result = self._request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "speckit-powerpack-edge-probe", "version": "0.1"},
        })
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        server = (result.get("serverInfo") or {})
        _log(f"MCP ready: {server.get('name', '?')} {server.get('version', '')}".strip())
        return result

    def call(self, name: str, arguments: dict, timeout: float = 240.0) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments}, timeout)
        chunks = [c.get("text", "") for c in (result.get("content") or []) if c.get("type") == "text"]
        text = "\n".join(chunks)
        if result.get("isError"):
            raise MCPError(f"tool {name} failed: {text[:800]}")
        return text

    def close(self) -> None:
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self._proc.kill()


# --------------------------------------------------------------------------- #
# JS run in the ChatGPT tab via evaluate_script. chrome-devtools-mcp 1.9.0
# rejects non-string `args`, so constants are BAKED into the source (%SEL%,
# %TEXT% → json.dumps) rather than passed as arguments. Each returns a string
# embedding {"__probe__": ...} so the Python side can extract it robustly.
# --------------------------------------------------------------------------- #
_JS_STATE_TMPL = """
() => {
  const sel = %SEL%;
  const q = (s) => document.querySelector(s);
  const stop = q(sel.stop);
  const turns = [...document.querySelectorAll(sel.assistant)];
  const last = turns[turns.length - 1];
  const login = !!q('a[href*="auth"], [data-testid="login-button"]')
    || location.hostname.includes('auth.openai.com');
  return JSON.stringify({__probe__: {
    url: location.href,
    login_wall: login,
    streaming: !!stop,
    assistant_count: turns.length,
    last_text: last ? (last.innerText || '') : '',
    has_composer: !!q(sel.composer),
  }});
}
"""

_JS_SEND_TMPL = """
async () => {
  const sel = %SEL%;
  const text = %TEXT%;
  const el = document.querySelector(sel.composer);
  if (!el) return JSON.stringify({__probe__: {sent: false, reason: 'composer not found'}});
  el.focus();
  try {
    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, text);
  } catch (e) {
    el.textContent = text;
    el.dispatchEvent(new InputEvent('input', {bubbles: true}));
  }
  await new Promise(r => setTimeout(r, 250));
  let btn = document.querySelector(sel.send);
  if (btn && !btn.disabled) { btn.click(); }
  else {
    el.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  }
  return JSON.stringify({__probe__: {sent: true, clicked: !!(btn && !btn.disabled)}});
}
"""

# Drives the REAL "@" mention autocomplete instead of typing "@GitHub" as plain
# text: types "@", waits for the picker, and clicks the entry containing
# "GitHub". ChatGPT's own frontend then resolves and inserts the real
# ecosystemMention chip (connector id + symbol offsets) — we never need to know
# the connector id ourselves. Falls back to a plain-text "@GitHub" if no picker
# shows up within the timeout (reported via `mention_engaged: false`).
_JS_SEND_MENTION_TMPL = """
async () => {
  const sel = %SEL%;
  const rest = %REST%;
  const el = document.querySelector(sel.composer);
  if (!el) return JSON.stringify({__probe__: {sent: false, reason: 'composer not found'}});
  el.focus();
  document.execCommand('selectAll', false, null);
  document.execCommand('delete', false, null);
  document.execCommand('insertText', false, '@');
  el.dispatchEvent(new InputEvent('input', {bubbles: true, data: '@', inputType: 'insertText'}));

  let item = null;
  for (let i = 0; i < 15 && !item; i++) {
    await new Promise(r => setTimeout(r, 200));
    const popup = document.querySelector(sel.mentionPopup);
    if (!popup) continue;
    const cands = [...popup.querySelectorAll(sel.mentionItem)];
    item = cands.find(c => (c.innerText || c.textContent || '').toLowerCase().includes('github'));
  }

  let mentionEngaged = false;
  if (item) {
    item.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true}));
    item.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
    item.click();
    await new Promise(r => setTimeout(r, 200));
    mentionEngaged = true;
  } else {
    document.execCommand('insertText', false, 'GitHub ');
  }
  if (rest) {
    document.execCommand('insertText', false, (mentionEngaged ? ' ' : '') + rest);
  }
  await new Promise(r => setTimeout(r, 250));
  let btn = document.querySelector(sel.send);
  if (btn && !btn.disabled) { btn.click(); }
  else {
    el.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  }
  return JSON.stringify({__probe__: {
    sent: true, mention_engaged: mentionEngaged, clicked: !!(btn && !btn.disabled),
  }});
}
"""


def _bake(tmpl: str, **subs: object) -> str:
    out = tmpl
    for key, val in subs.items():
        out = out.replace(f"%{key}%", json.dumps(val))
    return out

def _extract(text: str) -> dict:
    """Pull {"__probe__": {...}} out of an evaluate_script result. The JS returns
    JSON.stringify(...), which chrome-devtools-mcp may hand back raw or as an
    escaped JSON string; handle both, tolerating wrapper text and braces inside
    string values."""
    raw = text.find('{"__probe__"')
    if raw != -1:
        obj, _ = json.JSONDecoder().raw_decode(text[raw:])
        return obj["__probe__"]

    esc = text.find(r'{\"__probe__\"')
    if esc != -1:
        # find the enclosing double-quoted JSON string literal, unescape it once
        lo = text.rfind('"', 0, esc)
        hi = text.find('"', esc)
        while hi != -1 and text[hi - 1] == "\\":
            hi = text.find('"', hi + 1)
        if lo != -1 and hi != -1:
            inner = json.loads(text[lo:hi + 1])
            obj, _ = json.JSONDecoder().raw_decode(inner[inner.find("{"):])
            return obj["__probe__"]

    raise MCPError(f"no __probe__ payload in evaluate_script result:\n{text[:600]}")


# --------------------------------------------------------------------------- #
def _pages(client: MCPStdioClient, timeout: float = 60.0) -> tuple[list[tuple[int, str]], str]:
    """Returns (parsed [(id, url)], raw list_pages text). The raw text is kept so
    the first failure against real output is a one-line regex fix, not a guess."""
    raw = client.call("list_pages", {}, timeout=timeout)
    out: list[tuple[int, str]] = []
    for line in raw.splitlines():
        m = re.search(r"(\d+)\s*[:.\)]\s+(https?://\S+)", line)
        if m:
            out.append((int(m.group(1)), m.group(2).rstrip(")],")))
    return out, raw


def _eval(client: MCPStdioClient, page_id: int, js: str, timeout: float = 60.0) -> dict:
    raw = client.call("evaluate_script",
                      {"pageId": page_id, "function": js.strip(), "waitForStableDom": False},
                      timeout=timeout)
    return _extract(raw)


def human_wait(*, minimum: float = 1.5, maximum: float = 4.0) -> float:
    """Use a variable human-paced interval for browser observations."""
    duration = random.uniform(minimum, maximum)
    time.sleep(duration)
    return duration


def _await_answer(client: MCPStdioClient, page_id: int, sel: dict, *,
                  baseline: int, overall_timeout: float) -> str:
    deadline = time.monotonic() + overall_timeout
    grew = False
    stable_text = ""
    stable_hits = 0
    while time.monotonic() < deadline:
        human_wait()
        st = _eval(client, page_id, _bake(_JS_STATE_TMPL, SEL=sel))
        if st.get("login_wall"):
            raise MCPError("hit a login wall — sign in to the dedicated Edge profile once "
                           "(open the Edge window, log into chatgpt.com), then re-run.")
        if st["assistant_count"] > baseline:
            grew = True
        if not grew:
            continue
        text = st.get("last_text") or ""
        if st.get("streaming"):
            stable_hits = 0
            continue
        if text and text == stable_text:
            stable_hits += 1
            if stable_hits >= 2:
                return text
        else:
            stable_text = text
            stable_hits = 1
    raise MCPError(f"answer did not settle within {overall_timeout:.0f}s "
                   f"(streaming stuck or DOM selectors stale)")


# --------------------------------------------------------------------------- #
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", required=True,
                   help="ChatGPT Project URL (https://chatgpt.com/g/g-p-…) or a g-p-… id")
    p.add_argument("--pr", default="15", help="PR number for question 3 (default 15)")
    p.add_argument("--path", default=".", help="repo checkout (origin → owner/repo for Q3)")
    p.add_argument("--debug-url", default="",
                   help="connect straight to this HTTP CDP endpoint (e.g. http://localhost:9222) "
                        "and skip endpoint discovery")
    p.add_argument("--ws-endpoint", default="",
                   help="connect straight to this browser WebSocket endpoint "
                        "(ws://127.0.0.1:9222/devtools/browser/<id>) and skip discovery")
    p.add_argument("--port", type=int, default=9222,
                   help="debug port to discover/start on (default 9222)")
    p.add_argument("--launch", action="store_true",
                   help="if no debuggable Edge is found, start a DEDICATED one "
                        "(separate profile, sign in once). Without this, discovery-only.")
    p.add_argument("--relaunch-my-edge", action="store_true",
                   help="close ALL Edge windows and relaunch your DEFAULT profile (still "
                        "signed in) with --remote-debugging-port + --remote-allow-origins=*. "
                        "Use when discovery reports a 403.")
    p.add_argument("--edge-user-data", default="",
                   help="your live Edge profile dir for the DevToolsActivePort fallback "
                        "(Windows path; default %LOCALAPPDATA%\\Microsoft\\Edge\\User Data)")
    p.add_argument("--edge-user-data-dir", default="",
                   help="--launch: dedicated Edge profile dir (Windows path)")
    p.add_argument("--mcp-command", default="",
                   help="override the MCP server command (space-split; the endpoint flag is appended)")
    p.add_argument("--mention-github", action="store_true", default=True,
                   help="drive the REAL '@' autocomplete on questions 2 and 3: types '@', waits "
                        "for the picker, clicks the entry containing 'GitHub'. ChatGPT's own "
                        "frontend then resolves the connector id — this script never hardcodes "
                        "one. Falls back to literal '@GitHub ' text if no picker appears within "
                        "the timeout (reported per-turn as mention_engaged).")
    p.add_argument("--no-mention-github", dest="mention_github", action="store_false")
    p.add_argument("--sel-mention-popup", default='[role="listbox"]',
                   help="the '@' autocomplete popup container (guess; override + inspect "
                        "*-snapshot.txt if it never matches)")
    p.add_argument("--sel-mention-item", default='[role="option"]',
                   help="one entry inside --sel-mention-popup (guess)")
    p.add_argument("--answer-timeout", type=float, default=240.0,
                   help="seconds to wait for each answer to finish streaming (default 240)")
    p.add_argument("--first-call-timeout", type=float, default=45.0,
                   help="seconds for the first CDP call (list_pages) — a stall here means "
                        "the browser WebSocket is being refused (default 45)")
    p.add_argument("--verbose", action="store_true",
                   help="run chrome-devtools-mcp with DEBUG=* so its puppeteer/CDP logs "
                        "reach the stderr tail shown on failure")
    p.add_argument("--keep-open", action="store_true",
                   help="leave the MCP server + Edge tab open after the run")
    p.add_argument("--no-navigate", action="store_true",
                   help="drive whatever chatgpt.com tab is already open without navigating "
                        "it to --project first (use when the Project conversation is already up)")
    p.add_argument("--sel-composer", default='#prompt-textarea')
    p.add_argument("--sel-send", default='button[data-testid="send-button"]')
    p.add_argument("--sel-stop", default=(
        'button[data-testid="stop-button"],'
        'button[aria-label="Stop streaming"],'
        'button[aria-label="Stop generating"]'))
    p.add_argument("--sel-assistant", default='[data-message-author-role="assistant"]')
    args = p.parse_args()

    if not _is_wsl():
        _log("note: not running under WSL — assuming powershell.exe is still on PATH")

    # Resolve the Project URL + its g-p-… id (used to VERIFY we drive a tab that
    # is actually inside the Project — the whole reason this transport exists).
    proj = args.project.strip()
    if not proj.startswith("http"):
        proj = f"https://chatgpt.com/g/{proj}"
    pm = re.search(r"(g-p-[A-Za-z0-9]+)", proj)
    proj_id = pm.group(1) if pm else None
    _log(f"Project: {proj}" + (f"  (id {proj_id})" if proj_id else "  (WARNING: no g-p- id found)"))

    # owner/repo for question 3.
    try:
        url = subprocess.run(["git", "-C", str(Path(args.path).resolve()),
                              "remote", "get-url", "origin"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", check=True).stdout.strip()
        url = url.removesuffix(".git")
        repo = url.split("github.com:", 1)[1] if "github.com:" in url else \
            url.split("github.com/", 1)[1] if "github.com/" in url else "ds1david/specify-powerpack"
    except (OSError, subprocess.CalledProcessError, IndexError):
        repo = "ds1david/specify-powerpack"

    # Resolve a CDP endpoint: explicit flag > edge_chatgpt_launch.ps1 discovery
    # (HTTP probe → DevToolsActivePort of the live Edge) > dedicated --launch.
    endpoint_flag = ""  # "--browserUrl <url>" or "--wsEndpoint <ws>"
    if args.ws_endpoint:
        endpoint_flag = f"--wsEndpoint {args.ws_endpoint}"
    elif args.debug_url:
        endpoint_flag = f"--browserUrl {args.debug_url}"
    else:
        if not shutil.which("powershell.exe"):
            _log("powershell.exe not on PATH — pass --debug-url or --ws-endpoint explicitly"); return 2
        launcher_args = ["-Port", str(args.port)]
        if args.relaunch_my_edge:
            launcher_args.append("-Relaunch")
            mode = "relaunch my Edge"
        elif args.launch:
            mode = "discover + dedicated launch"
        else:
            launcher_args.append("-CheckOnly")
            mode = "discover only"
        if args.edge_user_data:
            launcher_args += ["-EdgeUserData", args.edge_user_data]
        if args.edge_user_data_dir:
            launcher_args += ["-UserDataDir", args.edge_user_data_dir]
        ps = _launcher_command(launcher_args)
        _log(f"resolving Edge CDP endpoint via edge_chatgpt_launch.ps1 ({mode}) …")
        # Windows PowerShell writes console text in an OEM/ANSI codepage, not
        # UTF-8 — decode lossily so accented diagnostics never crash the probe.
        try:
            r = subprocess.run(ps, text=True, encoding="utf-8", errors="replace",
                               capture_output=True, timeout=150, check=False)
            out, errtxt, rc_ps = r.stdout, r.stderr, r.returncode
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            errtxt = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            rc_ps = -1
            _log("launcher did not finish in 150s — using whatever endpoint it printed")
        for ln in _clean_ps(out + "\n" + errtxt).splitlines():
            _log(ln)
        m = re.search(r"^(?:CDP_URL|WS_URL)=(\S+)\s*$", out, re.MULTILINE)
        if not m:
            _log(f"launcher produced no endpoint (exit {rc_ps}). Most robust path: re-run "
                 "with --launch (dedicated Edge profile — a new window opens, sign in to "
                 "ChatGPT once, then re-run with --launch again)."); return 2
        url = m.group(1)
        endpoint_flag = (f"--wsEndpoint {url}" if url.startswith("ws")
                         else f"--browserUrl {url}")
        _log(f"endpoint: {url}")

    # Build the MCP server command (runs on Windows via PowerShell, mirroring a
    # working `powershell.exe -NoProfile -Command "npx.cmd …"` invocation).
    if args.mcp_command:
        mcp_cmd = [*args.mcp_command.split(), *endpoint_flag.split()]
    else:
        dbg = "$env:DEBUG='*'; " if args.verbose else ""
        inner = (f"{dbg}npx.cmd -y chrome-devtools-mcp@latest {endpoint_flag} "
                 f"--no-usage-statistics")
        mcp_cmd = ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
                   "-OutputFormat", "Text", "-Command", inner]

    questions = [
        "1) Qual é o nome deste projeto e descreva a missão do projeto em no máximo "
        "100 palavras? (use o contexto do Project).",
        "2) Liste todos os meus repositórios no GitHub. "
        "(use o Project como pano de fundo E o GitHub connector para os dados reais).",
        f"3) Liste apenas os arquivos modificados no pull request #{args.pr} do "
        f"repositório {repo}. (use o GitHub connector; siga a paginação até a lista ficar completa).",
    ]
    # Only Q2/Q3 need the GitHub connector; the '@' autocomplete is driven live
    # per turn (see _JS_SEND_MENTION_TMPL) — no connector id is hardcoded here.
    mention_turns = [False, args.mention_github, args.mention_github]

    report: dict[str, object] = {
        "transport": "edge-cdp chatgpt-web (chrome-devtools-mcp)",
        "experimental": True,
        "note": "not part of the supported provider — see DECISIONS_AND_TRADEOFFS.md §2 / SPEC-001 FR-020",
        "cdp_endpoint": endpoint_flag,
        "project_url_arg": proj,
        "project_id": proj_id,
        "project_url_observed": None,  # filled from the live tab; must contain project_id
        "repo": repo,
        "turn_mode": "threaded (one Web conversation, 3 messages)",
        "github_mention": ("drives the real '@' autocomplete + clicks the GitHub entry per turn "
                           "(mention_engaged in each turn's result says whether the picker was "
                           "found; false means it silently fell back to literal '@GitHub ' text)"
                           if args.mention_github else "none"),
        "turns": [],
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / "probe-edge-chatgpt-cdp.json"
    snap = EVIDENCE / "probe-edge-chatgpt-cdp-snapshot.txt"

    _log("if Edge shows \"Permitir depuração remota?\" — click \"Desativar nas "
         "configurações\" once (blocks CDP until answered)")
    client = MCPStdioClient(mcp_cmd)
    exit_code = 0
    try:
        client.initialize()

        sel = {"composer": args.sel_composer, "send": args.sel_send,
               "stop": args.sel_stop, "assistant": args.sel_assistant,
               "mentionPopup": args.sel_mention_popup, "mentionItem": args.sel_mention_item}

        # First browser-touching CDP call. chrome-devtools-mcp only connects
        # puppeteer to the endpoint HERE (not at initialize). A stall means the
        # WebSocket handshake is being refused — almost always because Edge was
        # started without --remote-allow-origins=*, or its "Allow remote
        # debugging?" modal is still up (it blocks ALL CDP until answered).
        _log("first CDP call (list_pages) — connecting to the browser now …")
        try:
            pages, pages_raw = _pages(client, timeout=args.first_call_timeout)
        except MCPError as exc:
            raise MCPError(
                f"{exc}\n\n"
                "The browser CDP WebSocket did not respond. Fixes, in order:\n"
                "  1. If Edge is showing \"Permitir depuração remota?\", click "
                "\"Desativar nas configurações\" and re-run.\n"
                "  2. Quit Edge COMPLETELY (check the tray) and relaunch it once with:\n"
                "       msedge.exe --remote-debugging-port=9222 --remote-allow-origins=*\n"
                "     then re-run. (Puppeteer's WS handshake needs that flag.)\n"
                "  3. Or run with --launch for a dedicated Edge profile that sets it.\n"
                "  4. Re-run with --verbose to see chrome-devtools-mcp's own logs.") from None
        _log(f"open tabs: {pages}")
        cand = [pid for pid, u in pages if "chatgpt.com" in u]
        if cand:
            page_id = cand[0]
        else:
            _log("no chatgpt.com tab — opening one")
            client.call("new_page", {"url": proj, "timeout": 45000}, timeout=75)
            human_wait()
            pages, pages_raw = _pages(client)
            cand = [pid for pid, u in pages if "chatgpt.com" in u]
            if not cand:
                raise MCPError(f"no chatgpt.com tab after new_page.\nlist_pages raw:\n{pages_raw}")
            page_id = cand[-1]
        client.call("select_page", {"pageId": page_id, "bringToFront": True}, timeout=30)
        report["browser_pages"] = pages
        _log(f"driving pageId={page_id}")

        if not args.no_navigate:
            client.call("navigate_page", {"pageId": page_id, "type": "url",
                                          "url": proj, "timeout": 45000}, timeout=75)

        # ChatGPT is a heavy SPA — list_pages URLs go stale and the project route
        # + composer take seconds to materialise. Poll the LIVE location + DOM
        # until the tab is on the Project and the composer exists (or a login
        # wall shows), before spending anything.
        st0 = {}
        for _ in range(20):
            human_wait()
            st0 = _eval(client, page_id, _bake(_JS_STATE_TMPL, SEL=sel))
            if st0.get("login_wall"):
                raise MCPError("login wall — open the Edge window, sign in to chatgpt.com "
                               "once (the DEDICATED profile if you used --launch), then re-run.")
            on_project = (not proj_id) or (proj_id in (st0.get("url") or ""))
            if on_project and st0.get("has_composer"):
                break
        report["project_url_observed"] = st0.get("url")
        if proj_id and proj_id not in (st0.get("url") or ""):
            raise MCPError(
                f"tab never landed inside Project {proj_id} (observed: {st0.get('url')}). "
                "Pass the exact Project URL, or --no-navigate if it is already open.")
        if not st0.get("has_composer"):
            snap.write_text(client.call("take_snapshot", {"pageId": page_id}), encoding="utf-8")
            raise MCPError(f"composer '{args.sel_composer}' never appeared — snapshot: {snap}")
        _log(f"Project binding OK: {st0.get('url')}")

        for i, question in enumerate(questions, start=1):
            st = _eval(client, page_id, _bake(_JS_STATE_TMPL, SEL=sel))
            if st.get("login_wall"):
                raise MCPError("login wall — sign in to the dedicated Edge profile once, then re-run.")
            if not st.get("has_composer"):
                snap.write_text(client.call("take_snapshot", {"pageId": page_id}), encoding="utf-8")
                raise MCPError(f"composer '{args.sel_composer}' not found — snapshot: {snap}")
            baseline = int(st.get("assistant_count") or 0)

            use_mention = mention_turns[i - 1]
            _log(f"turn {i}: sending{' (@ mention)' if use_mention else ''} …")
            if use_mention:
                sent = _eval(client, page_id, _bake(_JS_SEND_MENTION_TMPL, SEL=sel, REST=question))
            else:
                sent = _eval(client, page_id, _bake(_JS_SEND_TMPL, SEL=sel, TEXT=question))
            if not sent.get("sent"):
                raise MCPError(f"turn {i}: send failed: {sent.get('reason')}")
            if use_mention:
                _log(f"turn {i}: mention_engaged={sent.get('mention_engaged')}")

            text = _await_answer(client, page_id, sel, baseline=baseline,
                                 overall_timeout=args.answer_timeout)
            conv = _eval(client, page_id, _bake(_JS_STATE_TMPL, SEL=sel)).get("url", proj)
            report["conversation_url"] = conv
            print(f"\n=== TURN {i} ===\n{text}")
            report["turns"].append({"turn": i, "ok": True, "chars": len(text), "answer": text,
                                    "mention_engaged": sent.get("mention_engaged") if use_mention else None})

        _log("done")
    except KeyboardInterrupt:
        print("\n=== INTERRUPTED ===\nlast MCP server stderr:\n"
              f"{client._stderr_text()[-2500:]}", file=sys.stderr)
        report["turns"].append({"turn": len(report["turns"]) + 1, "ok": False,
                                "error": "KeyboardInterrupt"})
        exit_code = 130
    except (MCPError, subprocess.TimeoutExpired) as exc:
        print(f"\n=== ERROR ===\n{exc}", file=sys.stderr)
        report["turns"].append({"turn": len(report["turns"]) + 1, "ok": False, "error": str(exc)})
        exit_code = 1
    finally:
        if not args.keep_open:
            client.close()
        else:
            _log("--keep-open: MCP server + Edge left running")

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log(f"report: {out}")
    if report.get("conversation_url"):
        _log(f"conversation: {report['conversation_url']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
