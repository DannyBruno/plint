"""SKILL001: SKILL.md frontmatter completeness.

A skill needs name + description so the model can decide when to load it.
"""

from __future__ import annotations

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule


class SkillFrontmatterRule(Rule):
    id = "SKILL001"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []

        findings: list[Finding] = []
        for skill in bundle.skills:
            missing = []
            if not skill.frontmatter:
                missing.append("frontmatter")
            if not skill.frontmatter.get("name"):
                missing.append("name")
            if not skill.frontmatter.get("description"):
                missing.append("description")
            if not missing:
                continue
            findings.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.SKILL,
                    severity=Severity.ERROR if "frontmatter" in missing else Severity.WARN,
                    message=f"Skill '{skill.name}' is missing required frontmatter: {', '.join(missing)}.",
                    where=skill.name,
                    path=skill.path,
                    suggestion="Add YAML frontmatter with `name` and `description`. The description is what the model reads to decide whether to load the skill — make it start with 'Use this when…'.",
                    evidence={"missing": missing},
                )
            )
        return findings
