"""PROMPT001: Prompts over a length threshold likely contain task procedures that belong in skills."""

from __future__ import annotations

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule


class PromptLengthRule(Rule):
    id = "PROMPT001"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        warn_lines = int(cfg.options.get("warn_lines", config.prompt_warn_lines))
        error_lines = int(cfg.options.get("error_lines", config.prompt_error_lines))

        findings: list[Finding] = []
        for prompt in bundle.prompts:
            n = prompt.line_count
            if n >= error_lines:
                sev = Severity.ERROR
            elif n >= warn_lines:
                sev = Severity.WARN
            else:
                continue
            findings.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.PROMPT,
                    severity=sev,
                    message=f"Prompt '{prompt.name}' is {n} lines — long prompts often hide multi-step procedures that belong in skills.",
                    where=prompt.name,
                    path=prompt.path,
                    suggestion="Extract task-specific procedures into SKILL.md files and keep the base prompt focused on persona + routing.",
                    evidence={"lines": n, "warn_threshold": warn_lines, "error_threshold": error_lines},
                )
            )
        return findings
