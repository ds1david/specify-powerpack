"""Optional curl-style request trace.

When the ``SPECKIT_POWERPACK_HTTP_LOG`` environment variable names a file, every
outbound request the browserless flow makes is appended to it as a ``curl``
line — **method, URL and body only** (no headers, no token, no cookies), so the
trace is safe to read and share. Codex-CLI turns are recorded as a ``#`` note
with the command (prompt elided). A no-op when the variable is unset.
"""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import time

_ENV = "SPECKIT_POWERPACK_HTTP_LOG"
_MAX_BODY = 4096


def _target() -> Path | None:
    raw = os.environ.get(_ENV, "").strip()
    return Path(raw).expanduser() if raw else None


def _append(block: str) -> None:
    path = _target()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(block.rstrip("\n") + "\n")
    except OSError:
        pass


def curl(method: str, url: str, body: bytes | str | None = None) -> str:
    # URLs never contain a single quote in practice — wrap for copy-paste.
    parts = ["curl", "-sS", "-X", method.upper(), f"'{url}'"]
    if body is not None:
        text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)
        if len(text) > _MAX_BODY:
            text = text[:_MAX_BODY] + f"…[+{len(text) - _MAX_BODY} bytes]"
        parts += ["--data-raw", shlex.quote(text)]
    return " ".join(parts)


def log_request(method: str, url: str, body: bytes | str | None = None) -> None:
    _append(f"# {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n{curl(method, url, body)}")


def log_note(text: str) -> None:
    _append(f"# {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {text}")
