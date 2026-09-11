"""Optional curl-style request trace.

When the ``SPECKIT_POWERPACK_HTTP_LOG`` environment variable names a file, every
outbound request the browserless flow makes is appended to it as a ``curl``
line. Codex-CLI turns are recorded as a ``#`` note with the command (prompt
elided). A no-op when the variable is unset.

Two trace modes:

* **safe (default)** — method, URL and body only (no request headers).
  ``Bearer`` tokens and PAT-shaped strings that ride *inside* the body (e.g. a
  remote-MCP tool's ``headers.Authorization``) are redacted. Safe to read and
  share.
* **raw** — set ``SPECKIT_POWERPACK_HTTP_LOG_RAW`` to a truthy value
  (``1``/``true``/``yes``) and the trace becomes a byte-faithful, replayable
  ``curl``: **every request header** (Authorization bearer, cookies, conduit
  token, …), the **full unredacted, untruncated body**, one ``-H`` per line.
  The file then contains live credentials — do NOT commit or share it.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import time

_ENV = "SPECKIT_POWERPACK_HTTP_LOG"
_ENV_RAW = "SPECKIT_POWERPACK_HTTP_LOG_RAW"
_MAX_BODY = 4096

# `Bearer <token>` (auth headers serialized into a body) and bare GitHub token
# shapes (github_pat_…, ghp_/gho_/ghu_/ghs_/ghr_…). Redacted before the body is
# written or truncated, so a secret never lands in the shared trace.
_SECRET_RE = re.compile(
    r"(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}"
    r"|(github_pat_|gh[posur]_)[A-Za-z0-9_]{8,}"
)


def _redact(text: str) -> str:
    return _SECRET_RE.sub(lambda m: (m.group(1) or m.group(2) or "") + "<redacted>", text)


def _raw_mode() -> bool:
    return os.environ.get(_ENV_RAW, "").strip().lower() in {"1", "true", "yes", "on"}


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


def curl(
    method: str,
    url: str,
    body: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    """Render one request as a ``curl`` command.

    Safe mode (default): headers dropped, body redacted and truncated, single
    line. Raw mode (``SPECKIT_POWERPACK_HTTP_LOG_RAW`` truthy): every header
    emitted as ``-H``, body kept whole and unredacted, ``\\``-continued lines.
    """
    raw = _raw_mode()
    # URLs never contain a single quote in practice — wrap for copy-paste.
    head = f"curl -sS -X {method.upper()} '{url}'"

    body_arg = None
    if body is not None:
        text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)
        if not raw:
            text = _redact(text)
            if len(text) > _MAX_BODY:
                text = text[:_MAX_BODY] + f"…[+{len(text) - _MAX_BODY} bytes]"
        body_arg = f"--data-raw {shlex.quote(text)}"

    if not raw:
        # safe mode: no headers, single line
        return head if body_arg is None else f"{head} {body_arg}"

    # raw mode: every header + full body, one flag per continuation line
    lines = [head]
    for key, value in (headers or {}).items():
        lines.append(f"-H {shlex.quote(f'{key}: {value}')}")
    if body_arg is not None:
        lines.append(body_arg)
    return " \\\n  ".join(lines)


def log_request(
    method: str,
    url: str,
    body: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _append(f"# {stamp}\n{curl(method, url, body, headers)}")


def log_note(text: str) -> None:
    _append(f"# {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {text}")
