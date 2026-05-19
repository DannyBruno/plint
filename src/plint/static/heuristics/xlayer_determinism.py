"""XLAYER002: Deterministic operations expressed in prompt/skill text → belong in a tool.

Catches lines telling the model to do exact arithmetic, exact string transforms, ID lookups,
date math, etc. — the kind of work that is cheaper, safer, and more correct in code.
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_PATTERNS = [
    (re.compile(r"\bcalculate\b.*\b(sum|total|average|mean|count|product)\b", re.IGNORECASE), "arithmetic calculation"),
    (re.compile(r"\bcompute\b.*\b(hash|checksum|signature)\b", re.IGNORECASE), "cryptographic computation"),
    (re.compile(r"\bparse\b.*\b(json|xml|csv|yaml)\b", re.IGNORECASE), "structured-format parsing"),
    (re.compile(r"\b(format|convert)\b.*\b(date|timestamp|currency)\b", re.IGNORECASE), "date/currency formatting"),
    (re.compile(r"\blook ?up\b.*\b(database|db|table|record)\b", re.IGNORECASE), "database lookup"),
    (re.compile(r"\b(query|fetch|get)\b.*\b(api|endpoint)\b", re.IGNORECASE), "API call"),
    (re.compile(r"\b(encode|decode)\b.*\b(base64|url|utf-?8)\b", re.IGNORECASE), "encoding/decoding"),
]


def _scan(text: str) -> list[str]:
    hits = []
    for pat, label in _PATTERNS:
        if pat.search(text):
            hits.append(label)
    return hits


class XLayerDeterminismRule(Rule):
    id = "XLAYER002"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []

        findings: list[Finding] = []
        for prompt in bundle.prompts:
            hits = _scan(prompt.text)
            if hits:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.PROMPT,
                        severity=Severity.WARN,
                        message=f"Prompt '{prompt.name}' asks the model to perform deterministic operations ({', '.join(hits)}).",
                        where=prompt.name,
                        path=prompt.path,
                        suggestion="Move deterministic operations into a tool. Tools are cheaper, exact, and shield credentials — leave the model to decide *when* to call them.",
                        evidence={"detected": hits},
                    )
                )
        for skill in bundle.skills:
            hits = _scan(skill.body)
            if hits:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.INFO,
                        message=f"Skill '{skill.name}' describes deterministic operations ({', '.join(hits)}) — confirm these are exposed as tools.",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Skills can reference tools, but should not narrate the algorithm. Replace 'calculate the sum of X' with 'call the sum_tool with X'.",
                        evidence={"detected": hits},
                    )
                )
        return findings
