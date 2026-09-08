#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any


DEFAULT_PROMPT = (
    "@GitHub LISTE TODOS OS MEUS REPOSITORIOS E TERMINE A RESPOSTA COM "
    "POWERPACK_GITHUB_TOOL_OK"
)
MARKER = "POWERPACK_GITHUB_TOOL_OK"
SEND_SUFFIX = "/backend-api/f/conversation"
PREPARE_SUFFIX = "/backend-api/f/conversation/prepare"


class GitHubMentionNotResolved(RuntimeError):
    pass


class GitHubNetworkObserver:
    """Observe connector materialization without replacing Web2API's listener.

    ChatGPT-Web2API already owns Network.requestWillBeSent through its
    IdentityListener. This observer chains that handler and records only
    boolean/enum evidence; connector ids, headers, cookies, conduit and
    Sentinel/proof material are never retained in the report.
    """

    def __init__(self, driver) -> None:
        self.driver = driver
        self.mention_event = asyncio.Event()
        self.final_request_event = asyncio.Event()
        self.final_response_event = asyncio.Event()
        self.context_change: dict[str, Any] | None = None
        self.final_request: dict[str, Any] | None = None
        self.final_http_status: int | None = None
        self._final_request_id: str | None = None
        self._previous_request_handler = None
        self._previous_response_handler = None

    async def attach(self) -> None:
        handlers = self.driver._cdp_event_handlers
        self._previous_request_handler = handlers.get("Network.requestWillBeSent")
        self._previous_response_handler = handlers.get("Network.responseReceived")
        handlers["Network.requestWillBeSent"] = self._on_request
        handlers["Network.responseReceived"] = self._on_response
        # IdentityListener already enables Network with POST-body capture on
        # connect(). Re-enable idempotently with the same 4 MiB budget so this
        # probe remains explicit and survives listener re-attachment.
        await self.driver._cdp(
            "Network.enable",
            {"maxPostDataSize": 4 * 1024 * 1024},
            timeout=10,
        )

    def detach(self) -> None:
        handlers = self.driver._cdp_event_handlers
        if self._previous_request_handler is None:
            handlers.pop("Network.requestWillBeSent", None)
        else:
            handlers["Network.requestWillBeSent"] = self._previous_request_handler
        if self._previous_response_handler is None:
            handlers.pop("Network.responseReceived", None)
        else:
            handlers["Network.responseReceived"] = self._previous_response_handler

    @staticmethod
    def _body(message: dict[str, Any]) -> dict[str, Any] | None:
        request = ((message.get("params") or {}).get("request") or {})
        raw = request.get("postData")
        if not isinstance(raw, str) or not raw:
            return None
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _connector_hint(values: Any) -> bool:
        return any(
            isinstance(value, str) and value.startswith("plugin:connector_")
            for value in (values or [])
        )

    def _on_request(self, message: dict[str, Any]) -> None:
        if self._previous_request_handler is not None:
            self._previous_request_handler(message)
        try:
            params = message.get("params") or {}
            request = params.get("request") or {}
            if str(request.get("method") or "").upper() != "POST":
                return
            url = str(request.get("url") or "").split("?", 1)[0]
            if url.endswith(PREPARE_SUFFIX):
                body = self._body(message)
                if not body or body.get("client_prepare_source") != "context_change":
                    return
                partial = ""
                try:
                    partial = str(body["partial_query"]["content"]["parts"][0])
                except (KeyError, IndexError, TypeError):
                    pass
                connector = self._connector_hint(body.get("system_hints"))
                starts_github = partial.casefold().startswith("github ") or partial.casefold() == "github"
                self.context_change = {
                    "observed": True,
                    "connector_hint_present": connector,
                    "partial_query_starts_with_github": starts_github,
                    "client_prepare_state": str(body.get("client_prepare_state") or ""),
                    "client_prepare_dispatch": str(body.get("client_prepare_dispatch") or ""),
                }
                if connector and starts_github:
                    self.mention_event.set()
                return

            if not url.endswith(SEND_SUFFIX):
                return
            body = self._body(message)
            if not body:
                return
            messages = body.get("messages") or []
            first = messages[0] if messages and isinstance(messages[0], dict) else {}
            metadata = first.get("metadata") if isinstance(first, dict) else {}
            metadata = metadata if isinstance(metadata, dict) else {}
            serialization = metadata.get("serialization_metadata")
            serialization = serialization if isinstance(serialization, dict) else {}
            offsets = serialization.get("custom_symbol_offsets") or []
            ecosystem_mention = any(
                isinstance(item, dict) and item.get("symbol") == "ecosystemMention"
                for item in offsets
            )
            self.final_request = {
                "observed": True,
                "top_level_connector_hint": self._connector_hint(body.get("system_hints")),
                "message_connector_hint": self._connector_hint(metadata.get("system_hints")),
                "ecosystem_mention_present": ecosystem_mention,
                "client_prepare_state": str(body.get("client_prepare_state") or ""),
            }
            self._final_request_id = str(params.get("requestId") or "") or None
            self.final_request_event.set()
        except Exception:
            # Observability must never break Web2API's native send path.
            return

    def _on_response(self, message: dict[str, Any]) -> None:
        if self._previous_response_handler is not None:
            self._previous_response_handler(message)
        try:
            params = message.get("params") or {}
            if not self._final_request_id or str(params.get("requestId") or "") != self._final_request_id:
                return
            response = params.get("response") or {}
            self.final_http_status = int(response.get("status"))
            self.final_response_event.set()
        except Exception:
            return


async def run(args: argparse.Namespace) -> dict[str, Any]:
    from chatgpt_web2api.cdp_driver import CDPDriver

    if not args.prompt.lstrip().casefold().startswith("@github"):
        raise ValueError("Prompt must begin with @GitHub")

    driver = CDPDriver(
        cdp_port=args.cdp_port,
        tab_mode="owned",
        instance_id=f"powerpack-web2api-github-{args.cdp_port}",
    )
    observer: GitHubNetworkObserver | None = None
    original_type_message = None
    response_parts: list[str] = []
    try:
        await driver.connect()
        observer = GitHubNetworkObserver(driver)
        await observer.attach()
        await driver.navigate_new_chat(gizmo_id=args.project_id or None)
        if args.model and args.model != "auto":
            await driver.select_model(args.model)

        # Seam: send_and_stream owns baseline, IdentityListener, click_send,
        # response detection and anchored reconciliation. We change only the
        # type_message step: after Web2API types the full prompt, block the
        # transition to click_send until ChatGPT Web has resolved @GitHub into
        # a connector-aware context_change prepare.
        original_type_message = driver.type_message

        async def type_and_wait_for_github(text: str) -> None:
            await original_type_message(text)
            try:
                await asyncio.wait_for(observer.mention_event.wait(), timeout=args.mention_timeout)
            except TimeoutError as exc:
                raise GitHubMentionNotResolved(
                    "ChatGPT Web did not materialize @GitHub as a connector-aware "
                    "context_change before the send gate. Send was not clicked."
                ) from exc

        driver.type_message = type_and_wait_for_github

        async for chunk in driver.send_and_stream(
            args.prompt,
            timeout=args.response_timeout,
            model=args.model or "auto",
        ):
            if chunk.delta:
                response_parts.append(chunk.delta)

        # The final response event normally arrives while send_and_stream is
        # running. Give CDP a short grace period if dispatch ordering leaves it
        # pending after response reconciliation completes.
        if observer.final_request and observer.final_http_status is None:
            try:
                await asyncio.wait_for(observer.final_response_event.wait(), timeout=5.0)
            except TimeoutError:
                pass

        response = "".join(response_parts).strip()
        ctx = observer.context_change or {}
        final = observer.final_request or {}
        accepted = bool(
            ctx.get("connector_hint_present")
            and ctx.get("partial_query_starts_with_github")
            and final.get("top_level_connector_hint")
            and final.get("message_connector_hint")
            and final.get("ecosystem_mention_present")
            and observer.final_http_status == 200
            and MARKER in response
        )
        report: dict[str, Any] = {
            "ok": accepted,
            "stage": "web2api-github-flow",
            "classification": "WEB2API_GITHUB_FLOW_ACCEPTED" if accepted else "WEB2API_GITHUB_FLOW_INCOMPLETE",
            "request": {
                "transport": "chatgpt-web2api-cdpdriver",
                "project_scoped": bool(args.project_id),
                "prompt_starts_with_github": True,
                "direct_backend_submit_used": False,
                "sentinel_or_proof_fabricated": False,
                "network_headers_logged": False,
                "send_guarded_by_github_context_change": True,
            },
            "evidence": {
                "web2api_driver_connected": True,
                "github_context_change_prepare": bool(ctx.get("observed")),
                "connector_hint_present_before_send": bool(ctx.get("connector_hint_present")),
                "partial_query_starts_with_github": bool(ctx.get("partial_query_starts_with_github")),
                "final_submit_observed": bool(final.get("observed")),
                "final_top_level_connector_hint": bool(final.get("top_level_connector_hint")),
                "final_message_connector_hint": bool(final.get("message_connector_hint")),
                "final_ecosystem_mention": bool(final.get("ecosystem_mention_present")),
                "final_client_prepare_state": final.get("client_prepare_state"),
                "final_http_status": observer.final_http_status,
                "assistant_response_complete": bool(response),
                "marker_seen": MARKER in response,
            },
            "raw_secrets_included": False,
        }
        if args.include_assistant_text:
            report["assistant_text"] = response
        return report
    except GitHubMentionNotResolved as exc:
        return {
            "ok": False,
            "stage": "web2api-github-flow",
            "classification": "WEB2API_GITHUB_MENTION_NOT_RESOLVED",
            "error": str(exc),
            "evidence": {
                "web2api_driver_connected": True,
                "send_clicked": False,
                "github_context_change_prepare": bool(observer and observer.context_change),
            },
            "raw_secrets_included": False,
        }
    except Exception as exc:
        return {
            "ok": False,
            "stage": "web2api-github-flow",
            "classification": "WEB2API_CAPABILITY_BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
            "raw_secrets_included": False,
        }
    finally:
        if original_type_message is not None:
            driver.type_message = original_type_message
        if observer is not None:
            observer.detach()
        try:
            await driver.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Use ChatGPT-Web2API's own CDPDriver to materialize @GitHub before "
            "the native send_and_stream click/send/reconciliation path."
        )
    )
    parser.add_argument("--cdp-port", type=int, default=9231)
    parser.add_argument("--project-id", default="")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--mention-timeout", type=float, default=25.0)
    parser.add_argument("--response-timeout", type=float, default=240.0)
    parser.add_argument("--include-assistant-text", action="store_true")
    args = parser.parse_args()

    report = asyncio.run(run(args))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
