"""RUNTIME002: A→B→A→B oscillation between two tools."""

from __future__ import annotations

from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace


def detect_tool_oscillation(trace: Trace) -> list[Finding]:
    names = [t.name for _, t in trace.tool_calls()]
    for i in range(len(names) - 3):
        a, b, c, d = names[i : i + 4]
        if a == c and b == d and a != b:
            return [
                Finding(
                    rule_id="RUNTIME002",
                    layer=Layer.RUNTIME,
                    severity=Severity.WARN,
                    message=f"Tool oscillation detected: {a} ↔ {b} (4 consecutive calls).",
                    where=f"{a}↔{b}",
                    suggestion="The model is bouncing between two tools rather than committing. Often a sign the two tools have overlapping responsibilities — consider merging or clarifying their descriptions.",
                    evidence={"pattern": [a, b, c, d], "start_index": i},
                )
            ]
    return []
