"""PROMPT004: Emphasis cargo-culting — swear words, ALL CAPS runs, exclamation pile-ups.

From the paper: "We also have some swear words to try to get it to follow instructions."
That's a smell: modern models don't need emphasis hacks; this signals a prompt that's
asking the model to do more than it can do, or to override a missing guardrail.
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_SWEARS = {
    "damn",
    "damnit",
    "damnit",
    "fuck",
    "fucking",
    "shit",
    "bullshit",
    "hell",
    "crap",
    "goddamn",
    "godamn",
}
_CAPS_RUN = re.compile(r"\b[A-Z]{5,}\b")
_BANGS = re.compile(r"!{3,}")
_TOK = re.compile(r"\w+")


class PromptEmphasisRule(Rule):
    id = "PROMPT004"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []

        findings: list[Finding] = []
        for prompt in bundle.prompts:
            text = prompt.text
            lower_tokens = {t.lower() for t in _TOK.findall(text)}
            swears = sorted(lower_tokens & _SWEARS)
            caps = _CAPS_RUN.findall(text)
            bangs = _BANGS.findall(text)

            triggers = []
            if swears:
                triggers.append(f"swear words ({', '.join(swears)})")
            if len(caps) >= 5:
                triggers.append(f"{len(caps)} ALL-CAPS words")
            if bangs:
                triggers.append(f"{len(bangs)} '!!!' runs")
            if not triggers:
                continue

            findings.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.PROMPT,
                    severity=Severity.WARN,
                    message=f"Prompt '{prompt.name}' uses emphasis hacks: {'; '.join(triggers)}.",
                    where=prompt.name,
                    path=prompt.path,
                    suggestion="Modern models respond to structure, not volume. If you needed to shout, the underlying instruction is probably ambiguous or in the wrong layer (consider moving it to a tool guardrail or skill).",
                    evidence={"swears": swears, "caps_runs": len(caps), "exclamation_runs": len(bangs)},
                )
            )
        return findings
