"""PROMPT003: Procedural multi-step language in the base prompt → belongs in a skill.

Looks for:
  - Numbered step lists (3+ items)
  - Sequential connectives ("first…", "then…", "next…", "finally…")
  - "Step N:" patterns
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_NUMBERED = re.compile(r"^\s*(\d+)[.)]\s+\S", re.MULTILINE)
_STEP = re.compile(r"\bstep\s+\d+\b", re.IGNORECASE)
_CONNECTIVES = [
    re.compile(r"\bfirst\b[,:]?", re.IGNORECASE),
    re.compile(r"\bthen\b[,:]?", re.IGNORECASE),
    re.compile(r"\bnext\b[,:]?", re.IGNORECASE),
    re.compile(r"\bafter that\b", re.IGNORECASE),
    re.compile(r"\bfinally\b[,:]?", re.IGNORECASE),
]


class PromptProceduralRule(Rule):
    id = "PROMPT003"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        min_steps = int(cfg.options.get("min_steps", 3))
        min_connectives = int(cfg.options.get("min_connectives", 3))

        findings: list[Finding] = []
        for prompt in bundle.prompts:
            text = prompt.text

            numbered_hits = _NUMBERED.findall(text)
            step_hits = _STEP.findall(text)
            connective_hits = sum(len(p.findall(text)) for p in _CONNECTIVES)

            triggers: list[str] = []
            if len(numbered_hits) >= min_steps:
                triggers.append(f"{len(numbered_hits)} numbered list items")
            if len(step_hits) >= 2:
                triggers.append(f"{len(step_hits)} 'Step N' references")
            if connective_hits >= min_connectives:
                triggers.append(f"{connective_hits} sequential connectives (first/then/next/finally)")

            if not triggers:
                continue

            findings.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.PROMPT,
                    severity=Severity.WARN,
                    message=f"Prompt '{prompt.name}' encodes a multi-step procedure ({'; '.join(triggers)}).",
                    where=prompt.name,
                    path=prompt.path,
                    suggestion="Move step-by-step procedures into a SKILL.md so the prompt can stay focused on persona + when to invoke skills.",
                    evidence={
                        "numbered_items": len(numbered_hits),
                        "step_refs": len(step_hits),
                        "connectives": connective_hits,
                    },
                )
            )
        return findings
