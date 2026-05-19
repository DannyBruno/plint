"""TOOL002: Tool description quality.

Checks:
  - Missing or very short description
  - No example of when/why to call it
  - Vague action verbs ("handle", "process", "manage", "do")
  - Parameter count is huge with no required/optional separation
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_VAGUE_VERBS = re.compile(r"\b(handle|process|manage|do|deal with|work with)\b", re.IGNORECASE)


class ToolDescriptionRule(Rule):
    id = "TOOL002"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        min_chars = int(cfg.options.get("min_description_chars", config.tool_min_description_chars))

        findings: list[Finding] = []
        for tool in bundle.tools:
            desc = tool.description or ""
            triggers: list[str] = []

            if not desc.strip():
                triggers.append("missing description")
            elif len(desc) < min_chars:
                triggers.append(f"description only {len(desc)} chars (< {min_chars})")

            vague = _VAGUE_VERBS.findall(desc)
            if vague:
                triggers.append(f"vague verbs ({', '.join(set(v.lower() for v in vague))})")

            params = tool.parameters or {}
            props = params.get("properties", {}) if isinstance(params, dict) else {}
            if len(props) > 12 and not params.get("required"):
                triggers.append(f"{len(props)} parameters with no required list")

            if not triggers:
                continue

            findings.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.TOOL,
                    severity=Severity.WARN,
                    message=f"Tool '{tool.name}' has weak description metadata: {'; '.join(triggers)}.",
                    where=tool.name,
                    path=tool.path,
                    suggestion="Strong tool descriptions name the capability, when to use it, and at least one example. The model picks tools based on this text.",
                    evidence={"description_chars": len(desc), "triggers": triggers},
                )
            )
        return findings
