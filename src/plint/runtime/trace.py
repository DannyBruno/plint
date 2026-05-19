"""Provider-agnostic trace of model interactions."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolInvocation:
    name: str
    arguments: dict[str, Any]
    raw: dict[str, Any] | None = None

    def signature(self) -> str:
        """Stable hashable signature for loop detection."""

        return f"{self.name}({_canon(self.arguments)})"


@dataclass
class Call:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    provider: str = "unknown"
    model: str = ""
    started_at: float = field(default_factory=time.time)
    duration_s: float = 0.0
    # Inputs we extracted from the request
    system: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    tools_offered: list[dict[str, Any]] = field(default_factory=list)
    skills_offered: list[str] = field(default_factory=list)
    # Outputs we extracted from the response
    assistant_text: str = ""
    tool_calls: list[ToolInvocation] = field(default_factory=list)
    stop_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    # The original raw request/response for debugging
    raw_request: dict[str, Any] | None = None
    raw_response: Any = None


@dataclass
class Trace:
    calls: list[Call] = field(default_factory=list)

    def add(self, call: Call) -> None:
        self.calls.append(call)

    def tool_calls(self) -> list[tuple[Call, ToolInvocation]]:
        return [(c, t) for c in self.calls for t in c.tool_calls]


def _canon(obj: Any) -> str:
    """Deterministic-ish serialization for signatures."""

    if isinstance(obj, dict):
        return "{" + ",".join(f"{k}={_canon(obj[k])}" for k in sorted(obj)) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_canon(x) for x in obj) + "]"
    if isinstance(obj, str):
        return obj if len(obj) <= 80 else obj[:80] + "…"
    return str(obj)
