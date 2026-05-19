"""Monkey-patch Anthropic SDK Messages.create to record into the current session."""

from __future__ import annotations

import time
from typing import Any

from plint.runtime.session import current_session
from plint.runtime.trace import Call, ToolInvocation


def _extract_request(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": kwargs.get("model", ""),
        "system": kwargs.get("system"),
        "messages": list(kwargs.get("messages", [])),
        "tools": list(kwargs.get("tools", []) or []),
    }


def _extract_response(resp: Any) -> dict[str, Any]:
    text = ""
    tool_calls: list[ToolInvocation] = []
    try:
        for block in getattr(resp, "content", []) or []:
            btype = getattr(block, "type", None)
            if btype == "text":
                text += getattr(block, "text", "")
            elif btype == "tool_use":
                tool_calls.append(
                    ToolInvocation(
                        name=getattr(block, "name", ""),
                        arguments=dict(getattr(block, "input", {}) or {}),
                        raw={"id": getattr(block, "id", None), "type": "tool_use"},
                    )
                )
    except Exception:
        pass

    usage_raw = getattr(resp, "usage", None)
    usage: dict[str, int] = {}
    if usage_raw is not None:
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            v = getattr(usage_raw, k, None)
            if isinstance(v, int):
                usage[k] = v

    return {
        "assistant_text": text,
        "tool_calls": tool_calls,
        "stop_reason": getattr(resp, "stop_reason", None),
        "usage": usage,
    }


def _record(req: dict[str, Any], resp: Any, started: float) -> None:
    sess = current_session()
    if sess is None:
        return
    extracted = _extract_response(resp)
    call = Call(
        provider="anthropic",
        model=req.get("model", ""),
        started_at=started,
        duration_s=time.time() - started,
        system=req.get("system") if isinstance(req.get("system"), str) else None,
        messages=req.get("messages", []),
        tools_offered=req.get("tools", []),
        assistant_text=extracted["assistant_text"],
        tool_calls=extracted["tool_calls"],
        stop_reason=extracted["stop_reason"],
        usage=extracted["usage"],
    )
    sess.record(call)


def patch_anthropic(patched: list[tuple[object, str, object]]) -> bool:
    try:
        from anthropic.resources.messages import Messages
    except Exception:
        return False

    if getattr(Messages.create, "_plint_patched", False):
        return True

    original = Messages.create

    def create(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        req = _extract_request(kwargs)
        started = time.time()
        resp = original(self, *args, **kwargs)
        try:
            _record(req, resp, started)
        except Exception:
            pass
        return resp

    create._plint_patched = True  # type: ignore[attr-defined]
    Messages.create = create  # type: ignore[assignment]
    patched.append((Messages, "create", original))

    # Best-effort async patch
    try:
        from anthropic.resources.messages import AsyncMessages

        if not getattr(AsyncMessages.create, "_plint_patched", False):
            async_original = AsyncMessages.create

            async def acreate(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                req = _extract_request(kwargs)
                started = time.time()
                resp = await async_original(self, *args, **kwargs)
                try:
                    _record(req, resp, started)
                except Exception:
                    pass
                return resp

            acreate._plint_patched = True  # type: ignore[attr-defined]
            AsyncMessages.create = acreate  # type: ignore[assignment]
            patched.append((AsyncMessages, "create", async_original))
    except Exception:
        pass

    return True
