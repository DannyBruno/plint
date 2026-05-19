"""PROMPT002: Near-duplicate instructions in a single prompt.

Splits prompt into sentence-ish chunks and flags any chunk pair with high Jaccard overlap
on token shingles. Catches the "we wrote the same instruction several times" pattern.
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle, Prompt
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_TOKEN = re.compile(r"\w+")


def _shingles(text: str, k: int = 3) -> set[str]:
    toks = [t.lower() for t in _TOKEN.findall(text)]
    if len(toks) < k:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _find_duplicates(prompt: Prompt, threshold: float, min_tokens: int) -> list[tuple[str, str, float]]:
    chunks = [c.strip() for c in _SENT_SPLIT.split(prompt.text) if c.strip()]
    chunks = [c for c in chunks if len(_TOKEN.findall(c)) >= min_tokens]
    sh = [(c, _shingles(c)) for c in chunks]
    dupes: list[tuple[str, str, float]] = []
    seen: set[int] = set()
    for i in range(len(sh)):
        if i in seen:
            continue
        for j in range(i + 1, len(sh)):
            if j in seen:
                continue
            score = _jaccard(sh[i][1], sh[j][1])
            if score >= threshold:
                dupes.append((sh[i][0], sh[j][0], score))
                seen.add(j)
    return dupes


class PromptRepetitionRule(Rule):
    id = "PROMPT002"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        threshold = float(cfg.options.get("threshold", 0.6))
        min_tokens = int(cfg.options.get("min_tokens", 6))

        findings: list[Finding] = []
        for prompt in bundle.prompts:
            dupes = _find_duplicates(prompt, threshold, min_tokens)
            for a, b, score in dupes:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.PROMPT,
                        severity=Severity.WARN,
                        message=f"Prompt '{prompt.name}' repeats a near-identical instruction (similarity {score:.0%}).",
                        where=prompt.name,
                        path=prompt.path,
                        suggestion="Repeated instructions usually mean the model isn't obeying the first one. Add structure (headings, numbered steps) or move the instruction into a skill.",
                        evidence={"first": a[:160], "second": b[:160], "similarity": round(score, 2)},
                    )
                )
        return findings
