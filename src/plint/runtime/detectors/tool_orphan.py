"""RUNTIME003: tool was called but its output never makes it back into the conversation.

We look at the next call after a tool invocation. If the assistant's text doesn't reference
the tool's result in the next assistant turn (no matching tool_result message before the next
assistant generation), the call was wasted.
"""

from __future__ import annotations

from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace


def detect_tool_orphan(trace: Trace) -> list[Finding]:
    findings: list[Finding] = []
    for i, call in enumerate(trace.calls):
        if not call.tool_calls:
            continue
        next_call = trace.calls[i + 1] if i + 1 < len(trace.calls) else None
        if next_call is None:
            continue
        # If the next call's messages contain tool_result blocks for each tool_call, it's wired up.
        result_ids: set[str] = set()
        for msg in next_call.messages:
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") in ("tool_result", "function_call_output"):
                        tid = block.get("tool_use_id") or block.get("call_id") or block.get("tool_call_id")
                        if tid:
                            result_ids.add(str(tid))
        for tool in call.tool_calls:
            raw = tool.raw or {}
            tid = raw.get("id") or raw.get("call_id") or raw.get("tool_use_id")
            if tid and str(tid) not in result_ids:
                findings.append(
                    Finding(
                        rule_id="RUNTIME003",
                        layer=Layer.RUNTIME,
                        severity=Severity.WARN,
                        message=f"Tool call '{tool.name}' has no matching tool_result in the next turn — output was dropped.",
                        where=tool.name,
                        suggestion="Pass the tool's result back to the model in the next request, otherwise the call was wasted and the model is reasoning blind.",
                        evidence={"call_id": str(tid)},
                    )
                )
    return findings
