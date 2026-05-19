"""RUNTIME005: model output is full of hedging / assumption language.

Examples: "I'll assume…", "I'm not sure but…", "without more information, I'll guess…",
"could you clarify…". Frequent hedging indicates the upstream context was underspecified.
"""

from __future__ import annotations

import re

from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace

_HEDGES = [
    re.compile(r"\bi(?:'ll| will) assume\b", re.IGNORECASE),
    re.compile(r"\bi(?:'m| am) not sure\b", re.IGNORECASE),
    re.compile(r"\bnot entirely clear\b", re.IGNORECASE),
    re.compile(r"\bcould you (?:clarify|provide|share|confirm)\b", re.IGNORECASE),
    re.compile(r"\bwithout (?:more )?(?:information|context)\b", re.IGNORECASE),
    re.compile(r"\bi(?:'ll| will) guess\b", re.IGNORECASE),
    re.compile(r"\bif i understand correctly\b", re.IGNORECASE),
    re.compile(r"\bassuming (?:that|you mean|the)\b", re.IGNORECASE),
]


def _count_hedges(text: str) -> int:
    return sum(len(p.findall(text)) for p in _HEDGES)


def detect_hedging(trace: Trace, *, per_call_threshold: int = 2) -> list[Finding]:
    findings: list[Finding] = []
    total = 0
    for call in trace.calls:
        n = _count_hedges(call.assistant_text)
        total += n
        if n >= per_call_threshold:
            findings.append(
                Finding(
                    rule_id="RUNTIME005",
                    layer=Layer.RUNTIME,
                    severity=Severity.INFO,
                    message=f"Assistant response hedges {n}× — the prompt/skill may not give the model enough information to act.",
                    where=call.id,
                    suggestion="Check whether key context (user identity, prior turns, retrieved data) is being passed in. Hedging often means the model is filling gaps you didn't see.",
                    evidence={"hedge_count": n, "snippet": call.assistant_text[:240]},
                )
            )
    if not findings and total >= 3 and len(trace.calls) >= 3:
        findings.append(
            Finding(
                rule_id="RUNTIME005",
                layer=Layer.RUNTIME,
                severity=Severity.INFO,
                message=f"Hedging language appears across the session ({total} total) — suggests systemic context gaps.",
                where="session",
                suggestion="Audit what context the model has on each call. Are tool results, user metadata, and prior decisions making it into the prompt?",
                evidence={"total_hedges": total},
            )
        )
    return findings
