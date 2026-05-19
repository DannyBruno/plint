"""XLAYER001: The same instruction appears in two layers (prompt + skill, prompt + tool).

Cross-layer duplication is a code smell: when behavior changes, both copies drift.
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_TOK = re.compile(r"\w+")


def _shingles(text: str, k: int = 4) -> set[str]:
    toks = [t.lower() for t in _TOK.findall(text)]
    if len(toks) < k:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def _chunks(text: str, min_tokens: int = 8) -> list[str]:
    return [c.strip() for c in _SENT_SPLIT.split(text) if c.strip() and len(_TOK.findall(c)) >= min_tokens]


def _overlap(a_chunks: list[str], b_chunks: list[str], threshold: float) -> list[tuple[str, str, float]]:
    out: list[tuple[str, str, float]] = []
    a_sh = [(c, _shingles(c)) for c in a_chunks]
    b_sh = [(c, _shingles(c)) for c in b_chunks]
    for ac, ash in a_sh:
        for bc, bsh in b_sh:
            if not ash or not bsh:
                continue
            score = len(ash & bsh) / len(ash | bsh)
            if score >= threshold:
                out.append((ac, bc, score))
                break
    return out


class SeparationOverlapRule(Rule):
    id = "XLAYER001"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        threshold = float(cfg.options.get("threshold", 0.5))

        findings: list[Finding] = []
        for prompt in bundle.prompts:
            p_chunks = _chunks(prompt.text)
            if not p_chunks:
                continue
            for skill in bundle.skills:
                s_chunks = _chunks(skill.body)
                overlaps = _overlap(p_chunks, s_chunks, threshold)
                for pchunk, schunk, score in overlaps:
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.CROSS,
                            severity=Severity.WARN,
                            message=f"Prompt '{prompt.name}' and skill '{skill.name}' contain near-identical instructions ({score:.0%} overlap).",
                            where=f"{prompt.name} ↔ {skill.name}",
                            path=prompt.path,
                            suggestion="Pick one home for the instruction. Procedures belong in the skill; routing/persona belongs in the prompt.",
                            evidence={
                                "prompt_chunk": pchunk[:160],
                                "skill_chunk": schunk[:160],
                                "similarity": round(score, 2),
                            },
                        )
                    )
            for tool in bundle.tools:
                t_chunks = _chunks(tool.description)
                overlaps = _overlap(p_chunks, t_chunks, threshold)
                for pchunk, tchunk, score in overlaps:
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.CROSS,
                            severity=Severity.WARN,
                            message=f"Prompt '{prompt.name}' and tool '{tool.name}' description repeat the same guidance ({score:.0%} overlap).",
                            where=f"{prompt.name} ↔ {tool.name}",
                            path=prompt.path,
                            suggestion="The tool description is the source of truth for when to call the tool. Remove the duplicate from the prompt.",
                            evidence={
                                "prompt_chunk": pchunk[:160],
                                "tool_chunk": tchunk[:160],
                                "similarity": round(score, 2),
                            },
                        )
                    )
        return findings
