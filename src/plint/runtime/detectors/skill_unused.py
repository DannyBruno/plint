"""RUNTIME006: a skill was loaded into context but the assistant never referenced it.

Heuristic: if the prompt contains "skill:X" or a SKILL.md-style block tagged with a name,
and the assistant_text across the whole session never names that skill or follows its
distinctive steps, surface a finding so the team knows it's dead context.
"""

from __future__ import annotations

import re

from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace

_SKILL_MARKER = re.compile(r"(?:^|\n)#?\s*(?:skill|using skill|Skill:|<skill\s+name=)\s*[\"']?([a-zA-Z0-9_-]+)", re.IGNORECASE)


def detect_skill_unused(trace: Trace) -> list[Finding]:
    declared: dict[str, str] = {}  # skill_name -> first call id
    used: set[str] = set()
    for call in trace.calls:
        for name in call.skills_offered:
            declared.setdefault(name, call.id)
        if call.system:
            for m in _SKILL_MARKER.finditer(call.system):
                declared.setdefault(m.group(1), call.id)
        text = (call.assistant_text or "").lower()
        for name in list(declared.keys()):
            if name.lower() in text:
                used.add(name)

    findings: list[Finding] = []
    for name, first_call_id in declared.items():
        if name in used:
            continue
        findings.append(
            Finding(
                rule_id="RUNTIME006",
                layer=Layer.RUNTIME,
                severity=Severity.INFO,
                message=f"Skill '{name}' was loaded into context but never referenced by the assistant.",
                where=name,
                suggestion="Either narrow the conditions under which this skill is loaded, or sharpen its description so the model recognizes when to apply it.",
                evidence={"first_seen_call": first_call_id},
            )
        )
    return findings
