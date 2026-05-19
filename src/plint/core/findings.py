"""Findings model — what every rule emits."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class Layer(str, Enum):
    PROMPT = "prompt"
    SKILL = "skill"
    TOOL = "tool"
    RUNTIME = "runtime"
    CROSS = "cross"


@dataclass
class Finding:
    rule_id: str
    layer: Layer
    severity: Severity
    message: str
    where: str  # artifact name or trace span id
    path: Path | None = None
    line: int | None = None
    suggestion: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "layer": self.layer.value,
            "severity": self.severity.value,
            "message": self.message,
            "where": self.where,
            "path": str(self.path) if self.path else None,
            "line": self.line,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
        }


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    def by_severity(self) -> dict[Severity, list[Finding]]:
        out: dict[Severity, list[Finding]] = {s: [] for s in Severity}
        for f in self.findings:
            out[f.severity].append(f)
        return out

    def has_errors(self) -> bool:
        return any(f.severity == Severity.ERROR for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
        }
