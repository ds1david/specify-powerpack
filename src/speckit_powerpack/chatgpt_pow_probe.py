#!/usr/bin/env python3
# The implementation is moved into the installable package below; this file
# remains the standalone source entrypoint during the transition.
"""
chatgpt_pow_probe.py
--------------------
Script unico: token Codex (~/.codex/auth.json) + Sentinel PoW + Turnstile VM
+ prompt de teste no backend web do ChatGPT.

Uso:
  python3 chatgpt_pow_probe.py
  python3 chatgpt_pow_probe.py --prompt "Ola, responda so com pong"
  python3 chatgpt_pow_probe.py --auth ~/.codex/auth.json --model auto

Dependencias:
  pip install curl_cffi

Notas:
  - API nao oficial; pode quebrar a qualquer momento.
  - Turnstile aqui e a VM custom da OpenAI (dx XOR p), NAO o widget Cloudflare classico.
  - Se finalize/conversation falhar, o script imprime o body para diagnostico.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from curl_cffi import requests as cffi_requests
except ImportError as exc:
    # Keep the module importable for the packaged review path and unit tests.
    # The live web transport reports the actionable installation error when a
    # session is actually requested.
    cffi_requests = None
    _CURL_CFFI_IMPORT_ERROR = exc


BASE = "https://chatgpt.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
IMPERSONATE = "chrome131"
DEFAULT_AUTH = Path.home() / ".codex" / "auth.json"
POW_LIMIT = 800_000
LAST_CONVERSATION_ID = ""
LAST_DPL = ""
LAST_SCRIPT = ""
LAST_TOOL_INVOCATIONS: List[str] = []
LAST_AUTHORIZATION_REQUIRED = False
LAST_ALLOW_SENT = False
LAST_PARENT_MESSAGE_ID = ""

SCREEN_SIZES = [3000, 4000, 3120, 4160, 1920 + 1080, 2560 + 1440]
CPU_CORES = [8, 16, 24, 32]
NAV_KEYS = [
    "webdriver\u2212false",
    "cookieEnabled\u2212true",
    "language\u2212en-US",
    "vendor\u2212Google Inc.",
    "product\u2212Gecko",
    "platform\u2212Win32",
    "hardwareConcurrency\u22128",
    "pdfViewerEnabled\u2212true",
]
DOC_KEYS = ["location", "documentElement", "body", "head", "title", "URL"]
WIN_KEYS = [
    "window", "document", "navigator", "location", "screen",
    "performance", "crypto", "localStorage", "fetch",
]


def load_codex_auth(path: Path) -> Tuple[str, Optional[str]]:
    if not path.is_file():
        raise FileNotFoundError(f"auth nao encontrado: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    tokens = data.get("tokens") or {}
    access = (
        tokens.get("access_token")
        or data.get("access_token")
        or data.get("accessToken")
        or ""
    ).strip()
    if not access:
        raise ValueError(f"sem access_token em {path}")
    account = (
        tokens.get("account_id")
        or data.get("account_id")
        or data.get("chatgpt_account_id")
        or None
    )
    if account:
        account = str(account).strip() or None
    return access, account


def _time_string() -> str:
    now = datetime.now(timezone(timedelta(hours=-5)))
    return now.strftime("%a %b %d %Y %H:%M:%S") + " GMT-0500 (Eastern Standard Time)"


def build_config(user_agent: str, dpl: str = "", script: str = "") -> List[Any]:
    return [
        random.choice(SCREEN_SIZES),
        _time_string(),
        4294705152,
        0,
        user_agent,
        script or "",
        dpl or "",
        "en-US",
        "en-US,en",
        0,
        random.choice(NAV_KEYS),
        random.choice(DOC_KEYS),
        random.choice(WIN_KEYS),
        time.perf_counter() * 1000,
        str(uuid.uuid4()),
        "",
        random.choice(CPU_CORES),
        time.time() * 1000 - time.perf_counter() * 1000,
        0, 0, 0, 0, 0, 0, 0,
    ]


def solve_pow(seed: str, difficulty: str, config: List[Any], limit: int = POW_LIMIT) -> Tuple[str, bool]:
    if not difficulty:
        difficulty = "0fffff"
    seed_b = seed.encode()
    try:
        target = bytes.fromhex(difficulty)
    except ValueError:
        target = bytes.fromhex(difficulty.zfill(len(difficulty) + len(difficulty) % 2))
    n = max(1, len(target))
    p1 = (json.dumps(config[:3], separators=(",", ":"), ensure_ascii=False)[:-1] + ",").encode()
    p2 = ("," + json.dumps(config[4:9], separators=(",", ":"), ensure_ascii=False)[1:-1] + ",").encode()
    p3 = ("," + json.dumps(config[10:], separators=(",", ":"), ensure_ascii=False)[1:]).encode()
    for i in range(limit):
        raw = p1 + str(i).encode() + p2 + str(i >> 1).encode() + p3
        b64 = base64.b64encode(raw)
        digest = hashlib.sha3_512(seed_b + b64).digest()
        if digest[:n] <= target:
            return b64.decode("ascii"), True
    fallback = "wQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D" + base64.b64encode(f'"{seed}"'.encode()).decode()
    return fallback, False


def requirements_token(config: List[Any]) -> str:
    seed = format(random.random())
    ans, _ = solve_pow(seed, "0fffff", config, limit=200_000)
    return "gAAAAAC" + ans


def proof_token(seed: str, difficulty: str, config: List[Any]) -> str:
    ans, ok = solve_pow(seed, difficulty, config)
    if not ok:
        raise RuntimeError(f"PoW nao resolvido (difficulty={difficulty!r})")
    return "gAAAAAB" + ans


def fetch_dpl(session: Any) -> Tuple[str, str]:
    try:
        r = session.get(f"{BASE}/", timeout=20)
        html = r.text or ""
    except Exception as e:
        print(f"[warn] homepage falhou: {e}", file=sys.stderr)
        return "", ""
    dpl = ""
    m = re.search(r'<html[^>]*data-build="([^"]+)"', html, re.I)
    if m:
        dpl = m.group(1)
    scripts: List[str] = []
    for src in re.findall(r'<script[^>]+src="([^"]+)"', html, re.I):
        scripts.append(src)
        if not dpl:
            mm = re.search(r"c/[^/]+/_", src)
            if mm:
                dpl = mm.group(0)
    script = random.choice(scripts) if scripts else f"{BASE}/backend-api/sentinel/sdk.js"
    return dpl, script


class _OrderedMap:
    def __init__(self) -> None:
        self.keys: List[str] = []
        self.values: Dict[str, Any] = {}

    def add(self, key: str, value: Any) -> None:
        if key not in self.values:
            self.keys.append(key)
        self.values[key] = value


def _turnstile_to_str(value: Any) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        special = {
            "window.Math": "[object Math]",
            "window.Reflect": "[object Reflect]",
            "window.performance": "[object Performance]",
            "window.localStorage": "[object Storage]",
            "window.Object": "function Object() { [native code] }",
            "window.Reflect.set": "function set() { [native code] }",
            "window.performance.now": "function () { [native code] }",
            "window.Object.create": "function create() { [native code] }",
            "window.Object.keys": "function keys() { [native code] }",
            "window.Math.random": "function random() { [native code] }",
        }
        return special.get(value, value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return ",".join(value)
    return str(value)


def _xor_string(text: str, key: str) -> str:
    if not key:
        return text
    return "".join(chr(ord(ch) ^ ord(key[i % len(key)])) for i, ch in enumerate(text))


def solve_turnstile_token(dx: str, p: str) -> Optional[str]:
    """
    dx: base64 do bytecode.
    p: requirements token usado no prepare.

    Duas formas de decode tentadas:
      A) XOR byte-a-byte (base64decode(dx)[i] ^ p[i % len(p)]) -> utf-8 -> json
      B) base64decode -> utf-8 -> XOR string com p -> json  (legado)
    """
    token_list = None
    raw = None
    try:
        raw = base64.b64decode(dx)
    except Exception as e:
        print(f"[turnstile] b64decode falhou: {e}", file=sys.stderr)
        return None

    # A) XOR em bytes (forma descrita em reverses 2026)
    try:
        key = p.encode("utf-8")
        xored = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
        text_a = xored.decode("utf-8", errors="strict")
        token_list = json.loads(text_a)
        print(f"[turnstile] decode=A (byte-xor) instr={len(token_list) if isinstance(token_list, list) else type(token_list)}")
    except Exception as e_a:
        print(f"[turnstile] decode A falhou: {e_a}", file=sys.stderr)
        # B) legado string XOR
        try:
            text_b = raw.decode("utf-8", errors="strict")
            token_list = json.loads(_xor_string(text_b, p))
            print(f"[turnstile] decode=B (str-xor) instr={len(token_list) if isinstance(token_list, list) else type(token_list)}")
        except Exception as e_b:
            print(f"[turnstile] decode B falhou: {e_b}", file=sys.stderr)
            # C) raw utf-8 ignore + xor
            try:
                text_c = raw.decode("utf-8", errors="ignore")
                token_list = json.loads(_xor_string(text_c, p))
                print(f"[turnstile] decode=C instr={len(token_list) if isinstance(token_list, list) else type(token_list)}")
            except Exception as e_c:
                print(f"[turnstile] decode C falhou: {e_c}", file=sys.stderr)
                return None

    if not isinstance(token_list, list):
        print(f"[turnstile] token_list tipo={type(token_list)} sample={str(token_list)[:120]}", file=sys.stderr)
        return None

    # dump amostra para diagnostico (opcodes float randomizados)
    try:
        sample = token_list[:12]
        print("[turnstile] sample instr:")
        for i, ins in enumerate(sample):
            print(f"  [{i}] {ins}")
        # salva dump completo para analise offline
        dump_path = Path.home() / "chatgpt_turnstile_dump.json"
        dump_path.write_text(json.dumps({"p_prefix": p[:40], "n": len(token_list), "instr": token_list}, ensure_ascii=False)[:200000], encoding="utf-8")
        print(f"[turnstile] dump -> {dump_path}")
    except Exception as e:
        print(f"[turnstile] dump falhou: {e}", file=sys.stderr)

    process_map: Dict[Any, Any] = {}
    start_time = time.time()
    result = ""

    def func_1(e: float, t: float) -> None:
        process_map[e] = _xor_string(
            _turnstile_to_str(process_map.get(e)),
            _turnstile_to_str(process_map.get(t)),
        )

    def func_2(e: float, t: Any) -> None:
        process_map[e] = t

    def func_3(e: str) -> None:
        nonlocal result
        result = base64.b64encode(str(e).encode()).decode()

    def func_5(e: float, t: float) -> None:
        current = process_map.get(e)
        incoming = process_map.get(t)
        if isinstance(current, (list, tuple)):
            process_map[e] = list(current) + [incoming]
            return
        if isinstance(current, (str, float)) or isinstance(incoming, (str, float)):
            process_map[e] = _turnstile_to_str(current) + _turnstile_to_str(incoming)
            return
        process_map[e] = "NaN"

    def func_6(e: float, t: float, n: float) -> None:
        tv = process_map.get(t)
        nv = process_map.get(n)
        if isinstance(tv, str) and isinstance(nv, str):
            value = f"{tv}.{nv}"
            process_map[e] = "https://chatgpt.com/" if value == "window.document.location" else value

    def func_7(e: float, *args: float) -> None:
        target = process_map.get(e)
        values = [process_map.get(arg) for arg in args]
        if isinstance(target, str) and target == "window.Reflect.set":
            obj, key_name, val = values[0], values[1], values[2]
            if isinstance(obj, _OrderedMap):
                obj.add(str(key_name), val)
        elif callable(target):
            target(*values)

    def func_8(e: float, t: float) -> None:
        process_map[e] = process_map.get(t)

    def func_14(e: float, t: float) -> None:
        process_map[e] = json.loads(process_map[t])

    def func_15(e: float, t: float) -> None:
        process_map[e] = json.dumps(process_map[t], separators=(",", ":"))

    def func_17(e: float, t: float, *args: float) -> None:
        call_args = [process_map.get(arg) for arg in args]
        target = process_map.get(t)
        if target == "window.performance.now":
            elapsed_ns = time.time_ns() - int(start_time * 1e9)
            process_map[e] = (elapsed_ns + random.random()) / 1e6
        elif target == "window.Object.create":
            process_map[e] = _OrderedMap()
        elif target == "window.Object.keys":
            if call_args and call_args[0] == "window.localStorage":
                process_map[e] = [
                    "STATSIG_LOCAL_STORAGE_INTERNAL_STORE_V4",
                    "STATSIG_LOCAL_STORAGE_STABLE_ID",
                    "client-correlated-secret",
                    "oai/apps/capExpiresAt",
                    "oai-did",
                    "STATSIG_LOCAL_STORAGE_LOGGING_REQUEST",
                    "UiState.isNavigationCollapsed.1",
                ]
            elif call_args and isinstance(call_args[0], _OrderedMap):
                process_map[e] = list(call_args[0].keys)
            else:
                process_map[e] = []
        elif target == "window.Math.random":
            process_map[e] = random.random()
        elif callable(target):
            process_map[e] = target(*call_args)

    def func_18(e: float) -> None:
        process_map[e] = base64.b64decode(_turnstile_to_str(process_map.get(e))).decode()

    def func_19(e: float) -> None:
        process_map[e] = base64.b64encode(_turnstile_to_str(process_map.get(e)).encode()).decode()

    def func_20(e: float, t: float, n: float, *args: float) -> None:
        if process_map.get(e) == process_map.get(t):
            target = process_map.get(n)
            if callable(target):
                target(*[process_map.get(arg) for arg in args])

    def func_21(*_: Any) -> None:
        return

    def func_23(e: float, t: float, *args: float) -> None:
        if process_map.get(e) is not None and callable(process_map.get(t)):
            process_map[t](*args)

    def func_24(e: float, t: float, n: float) -> None:
        tv = process_map.get(t)
        nv = process_map.get(n)
        if isinstance(tv, str) and isinstance(nv, str):
            process_map[e] = f"{tv}.{nv}"

    process_map.update({
        1: func_1, 2: func_2, 3: func_3, 5: func_5, 6: func_6, 7: func_7, 8: func_8,
        9: token_list, 10: "window", 14: func_14, 15: func_15, 16: p,
        17: func_17, 18: func_18, 19: func_19, 20: func_20, 21: func_21, 23: func_23, 24: func_24,
    })

    # Execucao: tenta formato legado [opcode, *args] e formato novo [*args, opcode]
    # no sample atual o 3o elemento e int pequeno (1,3,7,13,15...) tipico de opcode
    ran = 0
    skipped = 0
    errors = 0
    op_counts: Dict[Any, int] = {}

    def _norm_op(op: Any) -> Any:
        if isinstance(op, float) and op == int(op):
            return int(op)
        return op

    def _call_op(op: Any, args: list) -> bool:
        op_key = _norm_op(op)
        fn = process_map.get(op_key)
        if not callable(fn):
            return False
        try:
            fn(*args)
            return True
        except TypeError:
            # alguns opcodes esperam contagem diferente de args
            try:
                if len(args) >= 1:
                    fn(*args[:1])
                    return True
            except Exception:
                pass
            raise

    for token in token_list:
        try:
            if not isinstance(token, (list, tuple)) or not token:
                skipped += 1
                continue

            # Heuristica: se ultimo elemento e int pequeno (0..40), tratar como opcode-last
            last = token[-1]
            first = token[0]
            used = False

            if isinstance(last, (int, float)) and _norm_op(last) in process_map and callable(process_map.get(_norm_op(last))):
                if isinstance(last, (int, float)) and 0 <= float(last) <= 40:
                    op_key = _norm_op(last)
                    op_counts[op_key] = op_counts.get(op_key, 0) + 1
                    if _call_op(op_key, list(token[:-1])):
                        ran += 1
                        used = True

            if not used:
                op_key = _norm_op(first)
                op_counts[op_key] = op_counts.get(op_key, 0) + 1
                if _call_op(op_key, list(token[1:])):
                    ran += 1
                else:
                    skipped += 1
        except Exception:
            errors += 1
            continue

    print(
        f"[turnstile] vm ran={ran} skipped={skipped} errors={errors} "
        f"result_len={len(result) if result else 0} ops={dict(list(sorted(op_counts.items(), key=lambda x: -x[1]))[:10])}"
    )
    return result or None



def make_session(access_token: str, device_id: str, session_id: str) -> Any:
    if cffi_requests is None:
        raise RuntimeError("The ChatGPT Web transport requires 'curl-cffi'; install the browserless extra.")
    s = cffi_requests.Session(impersonate=IMPERSONATE)
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": BASE,
        "Referer": f"{BASE}/",
        "OAI-Device-Id": device_id,
        "OAI-Session-Id": session_id,
        "OAI-Language": "en-US",
        "Authorization": f"Bearer {access_token}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })
    return s


def path_headers(path: str, extra: Optional[dict] = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "X-OpenAI-Target-Path": path,
        "X-OpenAI-Target-Route": path,
    }
    if extra:
        h.update(extra)
    return h


def get_chat_requirements(session: Any, config: List[Any]) -> Dict[str, str]:
    p = requirements_token(config)
    proof = ""
    turnstile = ""
    req_token = ""

    prepare_path = "/backend-api/sentinel/chat-requirements/prepare"
    try:
        r = session.post(
            BASE + prepare_path,
            headers=path_headers(prepare_path),
            json={"p": p},
            timeout=30,
        )
        if r.status_code == 404:
            raise FileNotFoundError("prepare 404")
        if r.status_code >= 400:
            print(f"[warn] prepare HTTP {r.status_code}: {r.text[:400]}", file=sys.stderr)
            raise RuntimeError("prepare failed")

        data = r.json()
        prepare_token = data.get("prepare_token") or ""
        print(f"[sentinel] prepare keys={list(data.keys())}")

        if (data.get("arkose") or {}).get("required"):
            raise RuntimeError("Arkose exigido — nao implementado")

        pow_info = data.get("proofofwork") or {}
        if pow_info.get("required"):
            seed = str(pow_info.get("seed") or "")
            diff = str(pow_info.get("difficulty") or "0fffff")
            print(f"[pow] prepare seed={seed[:28]}... difficulty={diff}")
            t0 = time.time()
            proof = proof_token(seed, diff, config)
            print(f"[pow] ok em {time.time() - t0:.2f}s")

        ts = data.get("turnstile") or {}
        if ts.get("required") and ts.get("dx"):
            print(f"[turnstile] dx len={len(ts['dx'])}")
            t0 = time.time()
            turnstile = solve_turnstile_token(ts["dx"], p) or ""
            if not turnstile:
                print("[turnstile] VM nao produziu token (opcodes float randomizados — solver legado incompativel)")
                print("[turnstile] tentando finalize SEM turnstile para ver resposta do servidor...")
            else:
                print(f"[turnstile] ok em {time.time() - t0:.2f}s token={turnstile[:32]}...")

        finalize_path = "/backend-api/sentinel/chat-requirements/finalize"
        fr = session.post(
            BASE + finalize_path,
            headers=path_headers(finalize_path),
            json={
                "prepare_token": prepare_token,
                "proof_token": proof,
                "turnstile_token": turnstile,
            },
            timeout=30,
        )
        if fr.status_code >= 400:
            print(f"[warn] finalize HTTP {fr.status_code}: {fr.text[:500]}", file=sys.stderr)
            raise RuntimeError("finalize failed")
        fdata = fr.json()
        req_token = fdata.get("token") or ""
        so_token = fdata.get("so_token") or ""
        if not req_token:
            raise RuntimeError(f"finalize sem token: {fdata}")
        print(f"[sentinel] finalize ok token={req_token[:28]}...")
        return {
            "token": req_token,
            "proof_token": proof,
            "turnstile_token": turnstile,
            "so_token": so_token,
        }
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[info] prepare/finalize: {e}; tentando legado...", file=sys.stderr)

    legacy_path = "/backend-api/sentinel/chat-requirements"
    r = session.post(
        BASE + legacy_path,
        headers=path_headers(legacy_path),
        json={"p": p},
        timeout=30,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"chat-requirements HTTP {r.status_code}: {r.text[:400]}")
    data = r.json()
    print(f"[sentinel] legacy keys={list(data.keys())}")

    if (data.get("arkose") or {}).get("required"):
        raise RuntimeError("Arkose exigido — nao implementado")

    pow_info = data.get("proofofwork") or {}
    if pow_info.get("required"):
        seed = str(pow_info.get("seed") or "")
        diff = str(pow_info.get("difficulty") or "0fffff")
        print(f"[pow] legacy seed={seed[:28]}... difficulty={diff}")
        t0 = time.time()
        proof = proof_token(seed, diff, config)
        print(f"[pow] ok em {time.time() - t0:.2f}s")

    ts = data.get("turnstile") or {}
    if ts.get("required") and ts.get("dx"):
        print(f"[turnstile] dx len={len(ts['dx'])}")
        t0 = time.time()
        turnstile = solve_turnstile_token(ts["dx"], p) or ""
        if not turnstile:
            print("[turnstile] VM nao produziu token no legado")
        else:
            print(f"[turnstile] ok em {time.time() - t0:.2f}s token={turnstile[:32]}...")

    req_token = data.get("token") or ""
    if not req_token:
        raise RuntimeError(f"chat-requirements sem token: {data}")
    return {
        "token": req_token,
        "proof_token": proof,
        "turnstile_token": turnstile,
        "so_token": data.get("so_token") or "",
    }


def build_conversation_body(
    prompt: str,
    model: str,
    *,
    project_id: Optional[str] = None,
    github_repos: Optional[List[str]] = None,
    connector_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    parent_message_id: str = "client-created-root",
    thinking_effort: Optional[str] = "extended",
) -> dict:
    """
    Payload alinhado ao HAR real (project + GitHub connector).

    O connector_id é obrigatório quando o GitHub é usado e deve vir da
    descoberta account-scoped do ChatGPT Web. Nunca use um ID observado em
    outra conta: a troca de conta/workspace pode gerar outro connector.

    Ativação:
      system_hints no top-level e em messages[0].metadata
      texto com prefixo @Github + serialization_metadata ecosystemMention
    """
    message_id = str(uuid.uuid4())
    github_repos = github_repos or []
    if github_repos and not connector_id:
        raise ValueError(
            "GitHub connector_id must be resolved for the current ChatGPT account"
        )
    if connector_id and not connector_id.startswith("plugin:"):
        connector_id = f"plugin:{connector_id}"

    system_hints: List[str] = []
    if connector_id:
        system_hints.append(connector_id)

    # Se GitHub ativo, espelha o composer: "@Github " + prompt
    text_parts = prompt
    custom_offsets = []
    if connector_id and not prompt.lstrip().lower().startswith("@github"):
        mention = "@Github "
        text_parts = mention + prompt
        custom_offsets = [
            {
                "id": connector_id,
                "symbol": "ecosystemMention",
                "startIndex": 0,
                "endIndex": len("@Github"),
            }
        ]

    msg_meta: Dict[str, Any] = {
        "serialization_metadata": {"custom_symbol_offsets": custom_offsets},
        "submission_mode": "manual_send",
    }
    if system_hints:
        msg_meta["system_hints"] = list(system_hints)
        msg_meta["selected_github_repos"] = list(github_repos)

    if project_id:
        conversation_mode: Dict[str, Any] = {
            "kind": "gizmo_interaction",
            "gizmo_id": project_id,
        }
    else:
        conversation_mode = {"kind": "primary_assistant"}

    body: Dict[str, Any] = {
        "action": "next",
        "messages": [
            {
                "id": message_id,
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [text_parts]},
                "metadata": msg_meta,
            }
        ],
        "parent_message_id": parent_message_id,
        "model": model,
        "client_prepare_state": "success",
        "timezone_offset_min": -180 if False else 180,  # HAR usou 180 (sinal UI)
        "timezone": "America/Sao_Paulo",
        "conversation_mode": conversation_mode,
        "enable_message_followups": True,
        "system_hints": system_hints,
        "model_response_contracts": [
            {
                "id": "photo_upload_action.v1",
                "protocol_version": 1,
                "presets": ["cap:image", "cap:file", "placement:end"],
            }
        ],
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "client_contextual_info": {
            "is_dark_mode": True,
            "time_since_loaded": random.randint(50, 200),
            "page_height": 889,
            "page_width": 1365,
            "pixel_ratio": 1,
            "screen_height": 1080,
            "screen_width": 1920,
            "app_name": "chatgpt.com",
            "has_web_push_capabilities": True,
            "web_push_notification_permission": "granted",
        },
        "paragen_cot_summary_display_override": "allow",
        "force_parallel_switch": "auto",
        "local_function_names": ["local.continue_in_work"],
    }
    if thinking_effort:
        body["thinking_effort"] = thinking_effort
    if conversation_id:
        body["conversation_id"] = conversation_id
    if project_id:
        body["gizmo_id"] = project_id
    return body



def conversation_headers(
    path: str,
    requirements: Dict[str, str],
    account_id: Optional[str],
    conduit: Optional[str] = None,
) -> dict:
    h = path_headers(path, {
        "Accept": "text/event-stream",
        "OpenAI-Sentinel-Chat-Requirements-Token": requirements["token"],
    })
    if requirements.get("proof_token"):
        h["OpenAI-Sentinel-Proof-Token"] = requirements["proof_token"]
    if requirements.get("turnstile_token"):
        h["OpenAI-Sentinel-Turnstile-Token"] = requirements["turnstile_token"]
    if requirements.get("so_token"):
        h["OpenAI-Sentinel-SO-Token"] = requirements["so_token"]
    if account_id:
        h["ChatGPT-Account-Id"] = account_id
    if conduit:
        h["x-conduit-token"] = conduit
    t1 = random.randint(1500, 4000)
    t2 = t1 + random.randint(200, 800)
    h["OAI-Echo-Logs"] = f"0,{t1},1,{t2}"
    return h


def try_conduit(session: Any, body: dict, account_id: Optional[str]) -> Optional[str]:
    for path in ("/backend-api/f/conversation/prepare", "/backend-api/conversation/prepare"):
        try:
            r = session.post(
                BASE + path,
                headers=path_headers(path, {"Accept": "application/json"}),
                json=body,
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                tok = data.get("conduit_token") or data.get("token")
                if tok:
                    print(f"[conduit] {path} -> {str(tok)[:24]}...")
                    return str(tok)
            elif r.status_code != 404:
                print(f"[conduit] {path} HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"[conduit] {path}: {e}", file=sys.stderr)
    return None


def parse_sse_assistant(response: Any) -> Tuple[str, Dict[str, Any]]:
    """Parse SSE. Returns (assistant_text, meta).

    meta pode conter:
      conversation_id, pending_allow: {target_message_id, parent_message_id}
    ``pending_allow`` só é preenchido para ``confirm_action`` explícito; um
    resultado normal de uma chamada já autorizada não dispara continuação.
    """
    global LAST_CONVERSATION_ID, LAST_TOOL_INVOCATIONS, LAST_AUTHORIZATION_REQUIRED, LAST_PARENT_MESSAGE_ID
    last_text = ""
    conversation_id = ""
    events = []
    raw_lines = []
    pending_allow: Dict[str, Any] = {}
    last_assistant_id = ""
    last_tool_call_id = ""
    tool_invocations: List[str] = []
    text_candidates: List[str] = []
    delta_text = ""

    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        raw_lines.append(line)
        if line.startswith("event:"):
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            if isinstance(payload, str) and payload.startswith('"'):
                events.append({"_raw_str": payload})
            continue
        if not isinstance(obj, dict):
            events.append({"_raw": obj})
            continue

        events.append({k: obj.get(k) for k in list(obj.keys())[:8]})

        # Final assistant text may arrive as JSON-patch append operations
        # followed by compact ``{"v": "..."}`` delta envelopes. Accumulate
        # the fragments; selecting only the last envelope would yield a
        # truncated review packet.
        if obj.get("o") == "patch" and isinstance(obj.get("v"), list):
            for operation in obj["v"]:
                if (
                    isinstance(operation, dict)
                    and operation.get("o") == "append"
                    and operation.get("p") == "/message/content/parts/0"
                    and isinstance(operation.get("v"), str)
                ):
                    delta_text += operation["v"]

        if obj.get("conversation_id"):
            conversation_id = obj["conversation_id"]
            LAST_CONVERSATION_ID = conversation_id
        if obj.get("error") or obj.get("detail"):
            raise RuntimeError(f"erro no stream: {obj.get('error') or obj.get('detail')}")
        if obj.get("type") == "error":
            raise RuntimeError(f"erro no stream: {obj}")

        # extract message from various shapes
        msg = None
        if isinstance(obj.get("message"), dict):
            msg = obj["message"]
        elif isinstance(obj.get("v"), dict) and isinstance(obj["v"].get("message"), dict):
            msg = obj["v"]["message"]
        elif obj.get("type") == "input_message" and isinstance(obj.get("input_message"), dict):
            msg = obj["input_message"]

        if msg:
            mid = msg.get("id") or ""
            author = (msg.get("author") or {})
            role = author.get("role")
            name = author.get("name")
            content = msg.get("content") or {}
            parts = content.get("parts") or []

            if role == "assistant":
                last_assistant_id = mid or last_assistant_id
                # tool call often appears as code content with JSON path /GitHub
                is_tool_call = content.get("content_type") == "code" or (
                    isinstance(content.get("text"), str) and "/GitHub" in content.get("text", "")
                )
                if is_tool_call:
                    last_assistant_id = mid or last_assistant_id
                    recipient = str(msg.get("recipient") or "")
                    # The Web API can encode the final JSON response as
                    # assistant.content.text. Tool-directed code is protocol
                    # state and must not be returned as the reviewer answer.
                    if recipient and not recipient.startswith("api_tool."):
                        candidate = content.get("text")
                        if isinstance(candidate, str) and candidate.strip():
                            text_candidates.append(candidate)
                if parts:
                    chunk = parts[-1]
                    if isinstance(chunk, str) and chunk.strip():
                        text_candidates.append(chunk)
                    elif isinstance(chunk, dict) and "text" in chunk:
                        text_candidates.append(str(chunk["text"]))
                # deltas in v
            if role == "tool" and name == "api_tool.call_tool":
                last_tool_call_id = mid or last_tool_call_id
            # A tool message is also emitted after an already-authorized
            # connector call. Only the explicit server confirmation action
            # means that the UI would show Allow/Deny. ChatGPT has emitted this
            # envelope with more than one message author/name across Web
            # continuations, so inspect the message metadata rather than
            # coupling authorization detection to one transport label.
            metadata = msg.get("metadata") or {}
            jit = metadata.get("jit_plugin_data") if isinstance(metadata, dict) else None
            from_server = jit.get("from_server") if isinstance(jit, dict) else None
            if isinstance(from_server, dict) and from_server.get("type") == "confirm_action":
                allow_target = last_assistant_id
                actions = from_server.get("actions")
                if isinstance(actions, list):
                    for action in actions:
                        if isinstance(action, dict) and action.get("type") == "allow":
                            allow_target = str(action.get("target_message_id") or allow_target)
                            break
                if allow_target:
                    pending_allow = {
                        "target_message_id": allow_target,
                        "parent_message_id": last_tool_call_id or mid,
                    }

            if role == "assistant" and parts:
                chunk = parts[-1]
                if isinstance(chunk, str) and chunk.strip() and not chunk.strip().startswith("{"):
                    last_text = chunk

        # v2 style content append
        if obj.get("v") and isinstance(obj["v"], str):
            delta_text += obj["v"]

        if obj.get("type") == "server_ste_metadata":
            md = obj.get("metadata") or {}
            if md.get("tool_invoked"):
                tool_name = str(md.get("tool_name") or "unknown")
                tool_invocations.append(tool_name)
                print(f"[sse] tool_invoked={tool_name}")

    if delta_text:
        last_text = delta_text
    elif text_candidates:
        last_text = text_candidates[-1]
    if conversation_id:
        print(f"[info] conversation_id={conversation_id}")
    print(f"[sse] events={len(events)} lines={len(raw_lines)}")
    for i, ev in enumerate(events[:12]):
        print(f"[sse] event[{i}]={json.dumps(ev, ensure_ascii=False)[:200]}")
    if pending_allow:
        print(f"[sse] pending_allow={pending_allow}")
        print("[auth] GitHub authorization requested: confirm_action detected")
    elif tool_invocations:
        print("[auth] GitHub authorization not requested: connector call continued")
    if not last_text and raw_lines:
        dump = Path.home() / "chatgpt_sse_dump.txt"
        try:
            dump.write_text("\n".join(raw_lines)[:50000], encoding="utf-8")
            print(f"[sse] raw dump -> {dump}")
        except OSError as exc:
            print(f"[sse] raw dump unavailable: {exc}", file=sys.stderr)

    meta = {
        "conversation_id": conversation_id or LAST_CONVERSATION_ID,
        "pending_allow": pending_allow,
        "tool_invocations": tuple(tool_invocations),
        "authorization_required": bool(pending_allow),
        "parent_message_id": last_assistant_id or last_tool_call_id,
    }
    LAST_TOOL_INVOCATIONS = tool_invocations
    LAST_AUTHORIZATION_REQUIRED = bool(pending_allow)
    LAST_PARENT_MESSAGE_ID = last_assistant_id or last_tool_call_id or LAST_PARENT_MESSAGE_ID
    return last_text.strip(), meta


def send_connector_allow(
    session: Any,
    requirements: Dict[str, str],
    *,
    conversation_id: str,
    parent_message_id: str,
    target_message_id: str,
    project_id: Optional[str],
    model: str,
    account_id: Optional[str],
    dpl: str = "",
    script: str = "",
) -> Tuple[str, Dict[str, Any]]:
    """POST allow for JIT GitHub connector permission (HAR-accurate)."""
    # 2o turno precisa de sentinel fresco (403 se reutilizar token velho)
    try:
        print("[allow] renovando sentinel...")
        cfg = build_config(UA, dpl=dpl, script=script)
        requirements = get_chat_requirements(session, cfg)
        print(f"[allow] sentinel ok token={requirements.get('token','')[:24]}...")
    except Exception as e:
        print(f"[allow] sentinel refresh falhou, reusando: {e}", file=sys.stderr)

    body: Dict[str, Any] = {
        "action": "next",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "author": {"role": "tool", "name": "api_tool.call_tool"},
                "content": {"content_type": "text", "parts": [""]},
                "recipient": "all",
                "metadata": {
                    "jit_plugin_data": {
                        "from_client": {
                            "type": "allow",
                            "target_message_id": target_message_id,
                            # Mirrors ChatGPT's "Allow GitHub for this
                            # conversation" action. If the account/project
                            # already granted access, no confirm_action is
                            # emitted and this continuation is never sent.
                            "remember_answer": True,
                        }
                    },
                },
            }
        ],
        "conversation_id": conversation_id,
        "parent_message_id": parent_message_id,
        "model": model,
        "client_prepare_state": "none",
        "timezone_offset_min": 180,
        "timezone": "America/Sao_Paulo",
        "conversation_mode": (
            {"kind": "gizmo_interaction", "gizmo_id": project_id}
            if project_id
            else {"kind": "primary_assistant"}
        ),
        "model_response_contracts": [
            {
                "id": "photo_upload_action.v1",
                "protocol_version": 1,
                "presets": ["cap:image", "cap:file", "placement:end"],
            }
        ],
        "supports_buffering": True,
        "supported_encodings": ["v1"],
        "client_contextual_info": {
            "is_dark_mode": True,
            "time_since_loaded": random.randint(80, 200),
            "page_height": 945,
            "page_width": 1365,
            "pixel_ratio": 1,
            "screen_height": 1080,
            "screen_width": 1920,
            "app_name": "chatgpt.com",
            "has_web_push_capabilities": True,
            "web_push_notification_permission": "granted",
        },
        "paragen_cot_summary_display_override": "allow",
        "force_parallel_switch": "auto",
        "local_function_names": ["local.continue_in_work"],
    }
    if project_id:
        body["messages"][0]["metadata"]["gizmo_id"] = project_id

    print(f"[allow] target={target_message_id} parent={parent_message_id}")
    print(
        f"[allow] tokens proof={'sim' if requirements.get('proof_token') else 'nao'} "
        f"turnstile={'sim' if requirements.get('turnstile_token') else 'nao'}"
    )
    path = "/backend-api/f/conversation"
    # Usar as mesmas chaves/headers do 1o turno (proof_token / turnstile_token)
    headers = conversation_headers(path, requirements, account_id, conduit=None)
    # Referer no contexto da conversa/project (como no HAR)
    if project_id:
        headers["Referer"] = f"{BASE}/g/{project_id}/c/{conversation_id}"
    else:
        headers["Referer"] = f"{BASE}/c/{conversation_id}"

    r = session.post(BASE + path, headers=headers, json=body, stream=True, timeout=180)
    print(f"[allow] POST HTTP {r.status_code}")
    if r.status_code >= 400:
        body_txt = r.text[:800]
        print(f"[allow] error body: {body_txt}", file=sys.stderr)
        raise RuntimeError(f"allow failed HTTP {r.status_code}: {body_txt[:200]}")
    return parse_sse_assistant(r)



def attach_conversation_to_project(session: Any, conversation_id: str, project_id: str) -> bool:
    """Tenta PATCH para mover conversa ao project (fallback se nao nasceu no gizmo)."""
    path = f"/backend-api/conversation/{conversation_id}"
    payloads = [
        {"project_id": project_id},
        {"gizmo_id": project_id},
        {"conversation_mode": {"kind": "gizmo_interaction", "gizmo_id": project_id}},
    ]
    for payload in payloads:
        try:
            r = session.patch(
                BASE + path,
                headers=path_headers(path, {"Accept": "application/json"}),
                json=payload,
                timeout=30,
            )
            print(f"[project] PATCH {payload} -> HTTP {r.status_code} {r.text[:120]}")
            if r.status_code < 400:
                return True
        except Exception as e:
            print(f"[project] PATCH falhou: {e}", file=sys.stderr)
    return False


def send_prompt(
    session: Any,
    requirements: Dict[str, str],
    prompt: str,
    model: str,
    account_id: Optional[str],
    *,
    project_id: Optional[str] = None,
    github_repos: Optional[List[str]] = None,
    connector_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    parent_message_id: str = "client-created-root",
    thinking_effort: Optional[str] = "extended",
) -> str:
    global LAST_ALLOW_SENT, LAST_TOOL_INVOCATIONS
    LAST_ALLOW_SENT = False
    body = build_conversation_body(
        prompt,
        model,
        project_id=project_id,
        github_repos=github_repos,
        connector_id=connector_id,
        conversation_id=conversation_id,
        parent_message_id=parent_message_id,
        thinking_effort=thinking_effort,
    )
    print(
        f"[chat] project={project_id or '-'} github={github_repos or []} "
        f"hints={body.get('system_hints')} model={model}"
    )
    conduit = try_conduit(session, body, account_id)
    paths = ["/backend-api/f/conversation", "/backend-api/conversation"]
    last_err = None
    for path in paths:
        headers = conversation_headers(path, requirements, account_id, conduit)
        print(f"[chat] POST {path}")
        r = session.post(BASE + path, headers=headers, json=body, timeout=120, stream=True)
        if r.status_code >= 400:
            text = ""
            try:
                text = r.text[:600]
            except Exception:
                pass
            last_err = f"{path} HTTP {r.status_code}: {text}"
            print(f"[warn] {last_err}", file=sys.stderr)
            continue
        text, meta = parse_sse_assistant(r)
        all_tool_invocations = list(LAST_TOOL_INVOCATIONS)
        if LAST_CONVERSATION_ID and project_id:
            attach_conversation_to_project(session, LAST_CONVERSATION_ID, project_id)

        # Auto-allow only explicit JIT confirmations. A deep review can make
        # several connector calls; each continuation is conditional and gets
        # fresh Sentinel credentials.
        for _ in range(8):
            pending = meta.get("pending_allow") or {}
            if not (
                pending.get("target_message_id")
                and pending.get("parent_message_id")
                and meta.get("conversation_id")
            ):
                break
            try:
                text2, meta = send_connector_allow(
                    session,
                    requirements,
                    conversation_id=meta["conversation_id"],
                    parent_message_id=pending["parent_message_id"],
                    target_message_id=pending["target_message_id"],
                    project_id=project_id,
                    model=model,
                    account_id=account_id,
                    dpl=LAST_DPL,
                    script=LAST_SCRIPT,
                )
                LAST_ALLOW_SENT = True
                all_tool_invocations.extend(name for name in LAST_TOOL_INVOCATIONS if name not in all_tool_invocations)
                text = text2 or text
            except Exception as e:
                print(f"[allow] falhou: {e}", file=sys.stderr)
                break

        if text:
            LAST_TOOL_INVOCATIONS = all_tool_invocations
            return text
        print("[chat] stream sem texto — tentando GET conversation")
        return text
    raise RuntimeError(last_err or "conversation falhou em todos os paths")


def probe_me(session: Any) -> None:
    try:
        r = session.get(f"{BASE}/backend-api/me", timeout=20)
        print(f"[probe] /me HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(
                "[probe] user:",
                json.dumps(
                    {k: data.get(k) for k in ("id", "email", "name", "phone_number") if k in data},
                    ensure_ascii=False,
                ),
            )
        else:
            print(f"[probe] body: {r.text[:200]}")
    except Exception as e:
        print(f"[probe] /me falhou: {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="ChatGPT web probe com Codex token + PoW + Turnstile VM")
    ap.add_argument("--auth", type=Path, default=DEFAULT_AUTH)
    ap.add_argument("--prompt", default="Responda apenas com a palavra: pong")
    ap.add_argument("--model", default="gpt-5-6-thinking")
    ap.add_argument("--skip-probe", action="store_true")
    ap.add_argument(
        "--project",
        default="g-p-6a9ba1a060208191a5b6e03a3950b183",
        help="Project gizmo id (g-p-...). Vazio para chat normal.",
    )
    ap.add_argument(
        "--github",
        action="append",
        default=None,
        help="owner/repo para selected_github_repos (pode repetir). Default: ds1david/specify-powerpack",
    )
    ap.add_argument("--conversation-id", default=None, help="continuar conversa existente")
    ap.add_argument("--parent-message-id", default="client-created-root")
    ap.add_argument("--no-project", action="store_true", help="nao usar project")
    ap.add_argument(
        "--connector",
        default=None,
        help="connector GitHub atual; se omitido, deve ser resolvido pelo chamador",
    )
    ap.add_argument("--no-github", action="store_true", help="nao ativar connector GitHub")
    args = ap.parse_args()
    if args.no_project:
        args.project = None
    if args.no_github:
        args.github = []
        args.connector = None
    elif args.github is None:
        args.github = ["ds1david/specify-powerpack"]

    print(f"[auth] lendo {args.auth}")
    access, account_id = load_codex_auth(args.auth)
    print(f"[auth] access_token len={len(access)} account_id={account_id or '-'}")

    device_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    session = make_session(access, device_id, session_id)

    if not args.skip_probe:
        probe_me(session)

    print("[dpl] homepage...")
    dpl, script = fetch_dpl(session)
    print(f"[dpl] build={dpl or '-'} script={(script or '-')[:70]}")

    global LAST_DPL, LAST_SCRIPT
    LAST_DPL = dpl
    LAST_SCRIPT = script
    config = build_config(UA, dpl=dpl, script=script)
    print("[sentinel] chat-requirements...")
    requirements = get_chat_requirements(session, config)
    print(
        "[sentinel] pronto "
        f"token={requirements['token'][:24]}... "
        f"proof={'sim' if requirements.get('proof_token') else 'nao'} "
        f"turnstile={'sim' if requirements.get('turnstile_token') else 'nao'}"
    )

    if args.github and not args.connector:
        # Resolve the connector in the same account-scoped session before
        # building the conversation payload. The connector id is not a
        # credential and must never be carried over from another account.
        try:
            from speckit_powerpack.chatgpt_project_provider import ChatGPTBackendClient
            from speckit_powerpack.github_connector_discovery import discover_github_connector

            resolved = discover_github_connector(
                ChatGPTBackendClient(args.auth),
                locale="pt-BR",
            )
            args.connector = resolved.connector_id
            print(f"[github] connector resolvido para a conta atual: {args.connector}")
        except Exception as exc:
            print(f"[erro] connector GitHub não resolvido para a conta atual: {exc}", file=sys.stderr)
            return 2

    print(f"[chat] model={args.model!r} prompt={args.prompt!r}")
    try:
        reply = send_prompt(
            session,
            requirements,
            args.prompt,
            args.model,
            account_id,
            project_id=args.project,
            github_repos=args.github,
            connector_id=getattr(args, "connector", None),
            conversation_id=args.conversation_id,
            parent_message_id=args.parent_message_id,
        )
    except Exception as e:
        print(f"[erro] conversation: {e}", file=sys.stderr)
        return 2

    if not reply and LAST_CONVERSATION_ID:
        print(f"[chat] buscando conteudo de {LAST_CONVERSATION_ID}...")
        try:
            import time as _t
            _t.sleep(2)
            gr = session.get(
                f"{BASE}/backend-api/conversation/{LAST_CONVERSATION_ID}",
                timeout=30,
            )
            print(f"[chat] GET conversation HTTP {gr.status_code}")
            if gr.status_code == 200:
                data = gr.json()
                mapping = data.get("mapping") or {}
                # pega ultima mensagem do assistant
                for node in mapping.values():
                    msg = (node or {}).get("message") or {}
                    if (msg.get("author") or {}).get("role") == "assistant":
                        parts = ((msg.get("content") or {}).get("parts")) or []
                        if parts and isinstance(parts[-1], str) and parts[-1].strip():
                            reply = parts[-1].strip()
        except Exception as e:
            print(f"[chat] GET conversation falhou: {e}", file=sys.stderr)

    print("\n======== RESPOSTA ========")
    print(reply or "(vazio)")
    print("==========================")
    if LAST_CONVERSATION_ID:
        print(f"[link] conversa: {BASE}/c/{LAST_CONVERSATION_ID}")
        if args.project:
            print(f"[link] project: {BASE}/g/{args.project}/project")
    print()
    return 0 if reply else 1


if __name__ == "__main__":
    sys.exit(main())
