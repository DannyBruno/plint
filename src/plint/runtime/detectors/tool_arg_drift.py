"""RUNTIME004: same tool called repeatedly with small arg perturbations → flailing."""

from __future__ import annotations

from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace, ToolInvocation


def _arg_similarity(a: ToolInvocation, b: ToolInvocation) -> float:
    if a.name != b.name:
        return 0.0
    keys = set(a.arguments) | set(b.arguments)
    if not keys:
        return 1.0
    matches = sum(1 for k in keys if a.arguments.get(k) == b.arguments.get(k))
    return matches / len(keys)


def detect_tool_arg_drift(trace: Trace, *, min_calls: int = 3, similarity_floor: float = 0.5) -> list[Finding]:
    findings: list[Finding] = []
    by_name: dict[str, list[ToolInvocation]] = {}
    for _, t in trace.tool_calls():
        by_name.setdefault(t.name, []).append(t)
    for name, calls in by_name.items():
        if len(calls) < min_calls:
            continue
        # Are all calls "similar but not identical"?
        sims = [_arg_similarity(calls[i], calls[i + 1]) for i in range(len(calls) - 1)]
        if not sims:
            continue
        avg_sim = sum(sims) / len(sims)
        all_unique = len({c.signature() for c in calls}) == len(calls)
        if all_unique and avg_sim >= similarity_floor:
            findings.append(
                Finding(
                    rule_id="RUNTIME004",
                    layer=Layer.RUNTIME,
                    severity=Severity.WARN,
                    message=f"Tool '{name}' called {len(calls)}× with small arg perturbations (avg similarity {avg_sim:.0%}) — model may be guessing.",
                    where=name,
                    suggestion="The model is iterating on arguments rather than reasoning about the result. Sharpen the tool's description, return more informative errors, or add an example to the prompt.",
                    evidence={"calls": len(calls), "avg_similarity": round(avg_sim, 2)},
                )
            )
    return findings
