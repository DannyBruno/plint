"""RUNTIME001: same tool called with same args in a tight window → loop."""

from __future__ import annotations

from collections import Counter

from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace


def detect_tool_loop(trace: Trace, *, window: int = 6, threshold: int = 3) -> list[Finding]:
    findings: list[Finding] = []
    signatures: list[tuple[str, int]] = []
    for idx, (_, tool) in enumerate(trace.tool_calls()):
        signatures.append((tool.signature(), idx))

    for i in range(len(signatures)):
        sl = signatures[i : i + window]
        counts = Counter(sig for sig, _ in sl)
        for sig, count in counts.items():
            if count >= threshold:
                findings.append(
                    Finding(
                        rule_id="RUNTIME001",
                        layer=Layer.RUNTIME,
                        severity=Severity.ERROR,
                        message=f"Tool call repeated {count}× in a {window}-call window: {sig}",
                        where=sig.split("(")[0],
                        suggestion="The model is stuck in a loop. Inspect whether the tool's output is unclear, the result isn't being added back to context, or the prompt doesn't tell the model when to stop.",
                        evidence={"signature": sig, "count": count, "window": window, "start_index": i},
                    )
                )
                return findings  # one finding per session is enough
    return findings
