from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable
import urllib.error
import urllib.parse
import urllib.request


BACKEND_API = "https://chatgpt.com/backend-api"
DEFAULT_AUTH_PATH = Path.home() / ".codex" / "auth.json"
PROJECT_ID_RE = re.compile(r"g-p-[A-Za-z0-9]+")


class ChatGPTProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class CodexAuth:
    access_token: str
    account_id: str
    auth_path: Path


@dataclass(frozen=True)
class ChatGPTProject:
    id: str
    name: str
    url: str
    raw: dict[str, Any]


def load_codex_auth(path: Path | None = None) -> CodexAuth:
    auth_path = (path or DEFAULT_AUTH_PATH).expanduser()
    if not auth_path.is_file():
        raise ChatGPTProjectError(
            f"Codex authentication file not found: {auth_path}. Run 'codex login' first."
        )
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChatGPTProjectError(f"Cannot read Codex authentication file {auth_path}: {exc}") from exc
    tokens = payload.get("tokens") if isinstance(payload, dict) else None
    if not isinstance(tokens, dict):
        raise ChatGPTProjectError("~/.codex/auth.json does not contain a 'tokens' object.")
    access_token = str(tokens.get("access_token") or "").strip()
    account_id = str(tokens.get("account_id") or "").strip()
    if not access_token:
        raise ChatGPTProjectError("~/.codex/auth.json does not contain an access_token. Run 'codex login' again.")
    if not account_id:
        account_id = _account_id_from_jwt(access_token)
    if not account_id:
        raise ChatGPTProjectError("Could not determine ChatGPT account_id from ~/.codex/auth.json.")
    return CodexAuth(access_token=access_token, account_id=account_id, auth_path=auth_path)


def _account_id_from_jwt(token: str) -> str:
    import base64

    parts = token.split(".")
    if len(parts) < 2:
        return ""
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded.encode()).decode("utf-8"))
    except Exception:
        return ""
    auth = claims.get("https://api.openai.com/auth") if isinstance(claims, dict) else None
    if isinstance(auth, dict):
        return str(auth.get("chatgpt_account_id") or "")
    return ""


def project_id_from_url_or_id(value: str) -> str:
    match = PROJECT_ID_RE.search(value or "")
    if not match:
        raise ChatGPTProjectError(f"Could not extract ChatGPT Project id (g-p-...) from: {value}")
    return match.group(0)


def _walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _project_from_dict(item: dict[str, Any]) -> ChatGPTProject | None:
    nested_gizmo = item.get("gizmo") if isinstance(item.get("gizmo"), dict) else None
    ids = [item.get("id"), item.get("gizmo_id"), nested_gizmo.get("id") if nested_gizmo else None]
    project_id = next((str(value) for value in ids if isinstance(value, str) and value.startswith("g-p-")), None)
    if not project_id:
        return None

    display = item.get("display") if isinstance(item.get("display"), dict) else {}
    nested_display = nested_gizmo.get("display") if nested_gizmo and isinstance(nested_gizmo.get("display"), dict) else {}
    name = next(
        (
            str(value).strip()
            for value in (
                item.get("name"),
                item.get("title"),
                display.get("name"),
                nested_gizmo.get("name") if nested_gizmo else None,
                nested_display.get("name"),
            )
            if isinstance(value, str) and value.strip()
        ),
        project_id,
    )
    short_url = next(
        (
            str(value).strip()
            for value in (
                item.get("short_url"),
                nested_gizmo.get("short_url") if nested_gizmo else None,
            )
            if isinstance(value, str) and value.strip()
        ),
        project_id,
    )
    if short_url.startswith("http://") or short_url.startswith("https://"):
        url = short_url.rstrip("/")
        if not url.endswith("/project"):
            url += "/project"
    else:
        url = f"https://chatgpt.com/g/{short_url}/project"
    return ChatGPTProject(id=project_id, name=name, url=url, raw=item)


class ChatGPTBackendClient:
    """Account-scoped reader for auth, Project context and connector discovery.

    Review generation is implemented by the separate ChatGPT Web SSE transport;
    this client remains the deterministic metadata/context boundary.
    """

    def __init__(self, auth_path: Path | None = None, *, timeout: int = 30):
        self.auth_path = auth_path or DEFAULT_AUTH_PATH
        self.timeout = timeout

    def _headers(self, *, accept: str = "application/json") -> dict[str, str]:
        auth = load_codex_auth(self.auth_path)
        return {
            "Authorization": f"Bearer {auth.access_token}",
            "ChatGPT-Account-ID": auth.account_id,
            "Accept": accept,
            "User-Agent": "speckit-powerpack/0.1",
        }

    def request_json(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = path if path.startswith("https://") else f"{BACKEND_API}{path}"
        raw_body = json.dumps(body).encode("utf-8") if body is not None else None
        headers = self._headers()
        if raw_body is not None:
            headers["Content-Type"] = "application/json"
        from .request_log import log_request

        log_request(method, url, raw_body, headers)
        req = urllib.request.Request(url, data=raw_body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401:
                raise ChatGPTProjectError(
                    "ChatGPT backend rejected ~/.codex/auth.json (401). Run 'codex login' again so Codex refreshes the account session."
                ) from exc
            raise ChatGPTProjectError(f"ChatGPT backend {method} {path} failed: HTTP {exc.code}: {detail[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise ChatGPTProjectError(f"Cannot reach ChatGPT backend: {exc}") from exc
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ChatGPTProjectError(f"ChatGPT backend returned invalid JSON for {path}: {raw[:500]}") from exc

    def validate_auth(self) -> dict[str, Any]:
        payload = self.request_json("GET", "/me")
        return payload if isinstance(payload, dict) else {"response": payload}

    def list_projects(self, *, limit: int = 50) -> list[ChatGPTProject]:
        payload = self.request_json("GET", f"/gizmos/snorlax/sidebar?limit={max(1, min(limit, 50))}")
        projects: dict[str, ChatGPTProject] = {}
        for item in _walk_dicts(payload):
            project = _project_from_dict(item)
            if project:
                existing = projects.get(project.id)
                if existing is None or existing.name == existing.id:
                    projects[project.id] = project
        return sorted(projects.values(), key=lambda p: p.name.casefold())

    def get_project(self, project_id_or_url: str) -> ChatGPTProject:
        project_id = project_id_from_url_or_id(project_id_or_url)
        payload = self.request_json("GET", f"/gizmos/{urllib.parse.quote(project_id)}")
        candidates = [_project_from_dict(item) for item in _walk_dicts(payload)]
        project = next((candidate for candidate in candidates if candidate and candidate.id == project_id), None)
        if project:
            return ChatGPTProject(project.id, project.name, project.url, payload if isinstance(payload, dict) else project.raw)
        return ChatGPTProject(
            project_id,
            project_id,
            f"https://chatgpt.com/g/{project_id}/project",
            payload if isinstance(payload, dict) else {},
        )

    def list_project_conversations(self, project_id_or_url: str, *, limit: int = 12) -> list[dict[str, Any]]:
        project_id = project_id_from_url_or_id(project_id_or_url)
        payload = self.request_json(
            "GET",
            f"/gizmos/{urllib.parse.quote(project_id)}/conversations?limit={max(1, min(limit, 50))}",
        )
        if isinstance(payload, dict):
            for key in ("items", "conversations"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        payload = self.request_json("GET", f"/conversation/{urllib.parse.quote(conversation_id)}")
        return payload if isinstance(payload, dict) else {}

    def build_project_context(
        self,
        project_id_or_url: str,
        *,
        max_conversations: int = 2,
        max_chars: int = 32_000,
    ) -> tuple[ChatGPTProject, str]:
        project = self.get_project(project_id_or_url)
        sections: list[str] = [
            f"CHATGPT PROJECT: {project.name}",
            f"PROJECT ID: {project.id}",
        ]
        metadata = _extract_project_metadata(project.raw)
        if metadata:
            sections.append("PROJECT METADATA / INSTRUCTIONS:\n" + metadata)

        conversations = self.list_project_conversations(project.id, limit=max_conversations)
        if conversations:
            sections.append("RECENT PROJECT CONVERSATIONS:")
        for item in conversations[:max_conversations]:
            conversation_id = str(item.get("id") or item.get("conversation_id") or "").strip()
            if not conversation_id:
                continue
            title = str(item.get("title") or conversation_id)
            try:
                full = self.get_conversation(conversation_id)
                transcript = _conversation_transcript(full, max_chars=8_000)
            except ChatGPTProjectError as exc:
                reason = str(exc)
                if "conversation_inaccessible" in reason or "don" in reason and "have access" in reason:
                    transcript = (
                        "[transcript not readable by the authenticated account — the ChatGPT "
                        "Project is shared but its conversation contents require the owner's "
                        "session or a per-conversation share link. Title above is the only signal.]"
                    )
                else:
                    transcript = f"[conversation could not be loaded: {exc}]"
            sections.append(f"\n### {title}\n{transcript}")
            if sum(len(part) for part in sections) >= max_chars:
                break
        bundle = "\n\n".join(sections)
        return project, bundle[:max_chars]


def _extract_project_metadata(payload: dict[str, Any]) -> str:
    found: list[str] = []
    seen: set[str] = set()
    interesting = {"instructions", "description", "name", "title", "context", "prompt_starters"}
    for item in _walk_dicts(payload):
        for key, value in item.items():
            if key not in interesting:
                continue
            if isinstance(value, str) and value.strip():
                text = f"{key}: {value.strip()}"
            elif isinstance(value, list) and value and all(isinstance(part, str) for part in value):
                text = f"{key}: " + " | ".join(part.strip() for part in value if part.strip())
            else:
                continue
            if text not in seen:
                seen.add(text)
                found.append(text)
    return "\n".join(found)[:16_000]


def _conversation_transcript(payload: dict[str, Any], *, max_chars: int) -> str:
    mapping = payload.get("mapping") if isinstance(payload, dict) else None
    if not isinstance(mapping, dict):
        return json.dumps(payload, ensure_ascii=False)[:max_chars]
    rows: list[tuple[float, str]] = []
    for node in mapping.values():
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        author = message.get("author") if isinstance(message.get("author"), dict) else {}
        role = str(author.get("role") or "unknown")
        content = message.get("content") if isinstance(message.get("content"), dict) else {}
        parts = content.get("parts")
        texts: list[str] = []
        if isinstance(parts, list):
            texts.extend(str(part) for part in parts if isinstance(part, (str, int, float)))
        text = content.get("text")
        if isinstance(text, str):
            texts.append(text)
        rendered = "\n".join(piece.strip() for piece in texts if piece.strip())
        if not rendered:
            continue
        create_time = message.get("create_time")
        try:
            order = float(create_time) if create_time is not None else 0.0
        except (TypeError, ValueError):
            order = 0.0
        rows.append((order, f"{role.upper()}: {rendered}"))
    rows.sort(key=lambda row: row[0])
    return "\n\n".join(text for _, text in rows)[-max_chars:]
