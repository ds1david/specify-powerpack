"""ChatGPT Web conversation transport used by the browserless review gate.

The transport is intentionally kept behind this adapter.  The low-level
Sentinel/SSE implementation remains reusable by the standalone probe while
the review flow supplies its already-resolved Project and GitHub connector.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from .chatgpt_project_provider import DEFAULT_AUTH_PATH, load_codex_auth


class ChatGPTWebReviewError(RuntimeError):
    """The non-browser ChatGPT Web transport could not be initialized."""


class ChatGPTWebReviewClient:
    """Run read-only review turns through ChatGPT Web's SSE conversation API.

    Permission is conditional: the transport only sends the JIT continuation
    when the stream contains the server's explicit ``confirm_action`` event.
    """

    def __init__(self, auth_path: Path | None = None):
        try:
            from . import chatgpt_pow_probe as transport
        except (ImportError, ModuleNotFoundError) as exc:
            raise ChatGPTWebReviewError(
                "ChatGPT Web transport is not packaged; install the browserless extra."
            ) from exc

        self.transport = transport
        try:
            auth = load_codex_auth(auth_path or DEFAULT_AUTH_PATH)
            self.session = transport.make_session(
                auth.access_token,
                str(uuid.uuid4()),
                str(uuid.uuid4()),
            )
        except Exception as exc:
            raise ChatGPTWebReviewError(str(exc)) from exc

        try:
            dpl, script = transport.fetch_dpl(self.session)
            transport.LAST_DPL = dpl
            transport.LAST_SCRIPT = script
            self.dpl = dpl
            self.script = script
        except Exception as exc:
            raise ChatGPTWebReviewError(f"Could not initialize ChatGPT Web Sentinel: {exc}") from exc

        self.account_id = auth.account_id
        self.last_tool_invocations: tuple[str, ...] = ()
        self.last_authorization_required = False
        self.last_allow_sent = False
        self.conversation_id = None
        self.parent_message_id = "client-created-root"

    def ask(
        self,
        prompt: str,
        *,
        project_id: str,
        connector_id: str,
        repository: str,
        model: str,
        effort: str = "xhigh",
        require_connector_evidence: bool = True,
    ) -> str:
        """Send one review turn, including dynamic Project and GitHub binding."""
        try:
            config = self.transport.build_config(
                self.transport.UA,
                dpl=self.dpl,
                script=self.script,
            )
            requirements = self.transport.get_chat_requirements(self.session, config)
            reply = self.transport.send_prompt(
                self.session,
                requirements,
                prompt,
                self._web_model(model),
                self.account_id,
                project_id=project_id,
                github_repos=[repository],
                connector_id=connector_id,
                conversation_id=self.conversation_id,
                parent_message_id=self.parent_message_id,
                thinking_effort=self._web_effort(effort),
            )
            self.last_tool_invocations = tuple(self.transport.LAST_TOOL_INVOCATIONS)
            self.last_authorization_required = bool(self.transport.LAST_AUTHORIZATION_REQUIRED)
            self.last_allow_sent = bool(self.transport.LAST_ALLOW_SENT)
            self.conversation_id = self.transport.LAST_CONVERSATION_ID or self.conversation_id
            self.parent_message_id = self.transport.LAST_PARENT_MESSAGE_ID or self.parent_message_id
            if require_connector_evidence and not self.last_tool_invocations:
                raise ChatGPTWebReviewError("ChatGPT Web response contained no connector/tool invocation evidence.")
            return reply
        except Exception as exc:
            raise ChatGPTWebReviewError(f"ChatGPT Web review turn failed: {exc}") from exc

    @staticmethod
    def _web_model(model: str) -> str:
        # The existing routing contract names the Codex reviewer as
        # ``gpt-5.6-sol``; the proven ChatGPT Web conversation route exposes
        # the corresponding web model as ``gpt-5-6-thinking``.
        if model in {"gpt-5.6-sol", "gpt-5.6-thinking"}:
            return "gpt-5-6-thinking"
        return model

    @staticmethod
    def _web_effort(effort: str) -> str:
        return "extended" if effort in {"high", "xhigh"} else effort
