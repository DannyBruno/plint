"""TOOL001: Tool description encodes a multi-step workflow.

Catches the "we just rewrote our workflow in tool calls" failure mode.
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_SEQ = [
    re.compile(r"\bfirst\b.*\bthen\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bstep\s*\d", re.IGNORECASE),
    re.compile(r"\bafter (that|this|you)\b", re.IGNORECASE),
    re.compile(r"\bonce (you|complete|done)\b", re.IGNORECASE),
    re.compile(r"\bfinally\b", re.IGNORECASE),
]
_BULLETED = re.compile(r"(?:^|\n)\s*[-*\d.]+\s+\S", re.MULTILINE)


class ToolWorkflowRule(Rule):
    id = "TOOL001"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []

        findings: list[Finding] = []
        for tool in bundle.tools:
            desc = tool.description or ""
            seq_hits = sum(1 for p in _SEQ if p.search(desc))
            bullets = len(_BULLETED.findall(desc))

            if seq_hits >= 2 or bullets >= 4 or (seq_hits >= 1 and len(desc) > 600):
                findings.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.TOOL,
                        severity=Severity.WARN,
                        message=f"Tool '{tool.name}' description reads like a workflow ({seq_hits} sequence markers, {bullets} bullet items, {len(desc)} chars).",
                        where=tool.name,
                        path=tool.path,
                        suggestion="Tools should expose a single, atomic capability. Multi-step procedures belong in skills; let the model orchestrate several small tools instead of one big one.",
                        evidence={
                            "sequence_markers": seq_hits,
                            "bullets": bullets,
                            "description_chars": len(desc),
                        },
                    )
                )
        return findings
