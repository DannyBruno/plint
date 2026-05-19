"""Monkey-patch OpenAI SDK chat.completions and responses to record into the current session.

This also covers OpenRouter because OpenRouter uses the OpenAI client with a custom base_url.
"""

from __future__ import annotations

import json
import time
from typing import Any

from plint.runtime.session import current_session
from plint.runtime.trace import Call, ToolInvocation


def _provider_from_client(client: Any) -> str:
    try:
        base = str(getattr(client, "base_url", "") or "")
        if "openrouter" in base:
            return "openrouter"
    except Exception:
        pass
    return "openai"


def _split_system(messages: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    sys_msgs = [m for m in messages if m.get("role") == "system"]
    others = [m for m in messages if m.get("role") != "system"]
    system = "\n\n".join(
        m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
        for m in sys_msgs
    ) or None
    return system, others


def _extract_chat_response(resp: Any) -> dict[str, Any]:
    text = ""
    tool_calls: list[ToolInvocation] = []
    stop_reason = None
    usage: dict[str, int] = {}
    try:
        choice = resp.choices[0]
        stop_reason = getattr(choice, "finish_reason", None)
        msg = choice.message
        text = getattr(msg, "content", None) or ""
        for tc in getattr(msg, "tool_calls", None) or []:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            try:
                args = json.loads(getattr(fn, "arguments", "") or "{}")
            except json.JSONDecodeError:
                args = {"_raw": getattr(fn, "arguments", "")}
            tool_calls.append(
                ToolInvocation(
                    name=getattr(fn, "name", ""),
                    arguments=args,
                    raw={"id": getattr(tc, "id", None), "type": "function"},
                )
            )
        u = getattr(resp, "usage", None)
        if u is not None:
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                v = getattr(u, k, None)
                if isinstance(v, int):
                    usage[k] = v
    except Exception:
        pass
    return {
        "assistant_text": text,
        "tool_calls": tool_calls,
        "stop_reason": stop_reason,
        "usage": usage,
    }


def _record_chat(client: Any, req_kwargs: dict[str, Any], resp: Any, started: float) -> None:
    sess = current_session()
    if sess is None:
        return
    messages = list(req_kwargs.get("messages", []))
    system, others = _split_system(messages)
    extracted = _extract_chat_response(resp)
    call = Call(
        provider=_provider_from_client(client),
        model=req_kwargs.get("model", ""),
        started_at=started,
        duration_s=time.time() - started,
        system=system,
        messages=others,
        tools_offered=list(req_kwargs.get("tools", []) or []),
        assistant_text=extracted["assistant_text"],
        tool_calls=extracted["tool_calls"],
        stop_reason=extracted["stop_reason"],
        usage=extracted["usage"],
    )
    sess.record(call)


def patch_openai(patched: list[tuple[object, str, object]]) -> bool:
    try:
        from openai.resources.chat.completions import Completions
    except Exception:
        return False

    if getattr(Completions.create, "_plint_patched", False):
        return True

    original = Completions.create

    def create(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        started = time.time()
        resp = original(self, *args, **kwargs)
        try:
            client = getattr(self, "_client", None) or getattr(self, "client", None)
            _record_chat(client, kwargs, resp, started)
        except Exception:
            pass
        return resp

    create._plint_patched = True  # type: ignore[attr-defined]
    Completions.create = create  # type: ignore[assignment]
    patched.append((Completions, "create", original))

    # Async
    try:
        from openai.resources.chat.completions import AsyncCompletions

        if not getattr(AsyncCompletions.create, "_plint_patched", False):
            async_original = AsyncCompletions.create

            async def acreate(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                started = time.time()
                resp = await async_original(self, *args, **kwargs)
                try:
                    client = getattr(self, "_client", None) or getattr(self, "client", None)
                    _record_chat(client, kwargs, resp, started)
                except Exception:
                    pass
                return resp

            acreate._plint_patched = True  # type: ignore[attr-defined]
            AsyncCompletions.create = acreate  # type: ignore[assignment]
            patched.append((AsyncCompletions, "create", async_original))
    except Exception:
        pass

    return True
