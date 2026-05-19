"""SKILL002 + SKILL003: Skill description specificity and body structure.

A skill that's just unstructured prose is a prompt in disguise. A skill whose
description doesn't help the model decide when to use it is useless context.
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_INVOKE_PATTERNS = [
    re.compile(r"\buse (this|when|for)\b", re.IGNORECASE),
    re.compile(r"\binvoke (this|when)\b", re.IGNORECASE),
    re.compile(r"\btrigger\b", re.IGNORECASE),
    re.compile(r"\bwhen\b.*\b(should|to)\b", re.IGNORECASE),
]
_HEADING = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+\S", re.MULTILINE)
_BULLET = re.compile(r"^\s*[-*]\s+\S", re.MULTILINE)


class SkillSpecificityRule(Rule):
    id = "SKILL002"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []

        findings: list[Finding] = []
        for skill in bundle.skills:
            desc = skill.description or ""
            if not desc:
                continue
            if not any(p.search(desc) for p in _INVOKE_PATTERNS):
                findings.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.WARN,
                        message=f"Skill '{skill.name}' description doesn't tell the model when to invoke it.",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Start the description with 'Use this when…' so the model can match it against a task. Anthropic skill examples follow this pattern.",
                        evidence={"description": desc[:200]},
                    )
                )

            body = skill.body or ""
            headings = len(_HEADING.findall(body))
            numbered = len(_NUMBERED.findall(body))
            bullets = len(_BULLET.findall(body))
            non_empty_lines = sum(1 for ln in body.splitlines() if ln.strip())
            if non_empty_lines >= 20 and headings == 0 and numbered == 0 and bullets < 3:
                findings.append(
                    Finding(
                        rule_id="SKILL003",
                        layer=Layer.SKILL,
                        severity=Severity.WARN,
                        message=f"Skill '{skill.name}' body has no procedural structure (no headings, no numbered steps, few bullets) — it reads like a prompt in disguise.",
                        where=skill.name,
                        path=skill.path,
                        suggestion="A skill should be a procedure. Use numbered steps or `## Section` headings so the model can follow it as a recipe.",
                        evidence={
                            "lines": non_empty_lines,
                            "headings": headings,
                            "numbered": numbered,
                            "bullets": bullets,
                        },
                    )
                )
        return findings
