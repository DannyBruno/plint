"""Prompt rules grounded in Anthropic's prompt-engineering best-practices guide.

  PROMPT005 — soft override emphasis (MUST / CRITICAL / ALWAYS / NEVER inline in body)
  PROMPT006 — predominantly negative phrasing ("Do not… / never… / don't…")
  PROMPT007 — system prompt missing a role/persona declaration
  PROMPT008 — long prompt with no XML structuring tags
  PROMPT009 — long prompt with no few-shot examples
  PROMPT010 — long-context-style prompt where the imperative appears at the top rather than the end
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_HEADING = re.compile(r"^\s*#{1,6}\s", re.MULTILINE)
_SOFT_EMPHASIS_INLINE = re.compile(
    r"(?<!^)(?<!\n)(?<![#>])\s\b(MUST|CRITICAL|ALWAYS|NEVER|YOU MUST|DO NOT EVER)\b",
)
_NEGATIVE_INSTRUCTION = re.compile(r"\b(do not|don'?t|never|avoid|refuse to)\b", re.IGNORECASE)
_INSTRUCTION_SENT = re.compile(r"[.!?]")
_ROLE_PATTERNS = [
    re.compile(r"\byou are\b", re.IGNORECASE),
    re.compile(r"\bact as\b", re.IGNORECASE),
    re.compile(r"\bplay the role of\b", re.IGNORECASE),
    re.compile(r"\byour role is\b", re.IGNORECASE),
]
_XML_TAG = re.compile(r"<[a-zA-Z][a-zA-Z0-9_:-]*\b[^>]*>")
_EXAMPLE_TAG = re.compile(r"<example[s]?\b", re.IGNORECASE)


class PromptSoftEmphasisRule(Rule):
    id = "PROMPT005"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for prompt in bundle.prompts:
            # Skip lines that are markdown headings — `## CRITICAL: …` headers are fine.
            body_lines = [ln for ln in prompt.lines if not _HEADING.match(ln)]
            body = "\n".join(body_lines)
            hits = _SOFT_EMPHASIS_INLINE.findall(body)
            if len(hits) >= 3:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.PROMPT,
                        severity=Severity.INFO,
                        message=f"Prompt '{prompt.name}' uses inline override language {len(hits)}× (MUST/CRITICAL/ALWAYS/NEVER).",
                        where=prompt.name,
                        path=prompt.path,
                        suggestion="Anthropic's prompting guide notes that aggressive override language can cause newer models to overtrigger. Prefer 'Use this when…' phrasing or move the directive into a structural `## Important` header.",
                        evidence={"count": len(hits), "tokens": list(set(hits))[:5]},
                    )
                )
        return out


class PromptNegativeInstructionRule(Rule):
    id = "PROMPT006"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        ratio_threshold = float(cfg.options.get("ratio", 0.4))
        min_neg = int(cfg.options.get("min_negative", 5))
        out: list[Finding] = []
        for prompt in bundle.prompts:
            text = prompt.text
            neg = len(_NEGATIVE_INSTRUCTION.findall(text))
            if neg < min_neg:
                continue
            sentences = max(1, len(_INSTRUCTION_SENT.findall(text)))
            ratio = neg / sentences
            if ratio >= ratio_threshold:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.PROMPT,
                        severity=Severity.INFO,
                        message=f"Prompt '{prompt.name}' leans heavily on negative instructions ({neg} hits in ~{sentences} sentences, {ratio:.0%}).",
                        where=prompt.name,
                        path=prompt.path,
                        suggestion="Anthropic's prompting guide recommends positive phrasing — 'Respond in flowing prose' beats 'Do not use markdown'. Models follow what to DO better than what NOT to do.",
                        evidence={"negative_hits": neg, "sentences": sentences, "ratio": round(ratio, 2)},
                    )
                )
        return out


class PromptRoleRule(Rule):
    id = "PROMPT007"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for prompt in bundle.prompts:
            if prompt.role != "system":
                continue
            if not any(p.search(prompt.text) for p in _ROLE_PATTERNS):
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.PROMPT,
                        severity=Severity.INFO,
                        message=f"System prompt '{prompt.name}' has no role/persona declaration.",
                        where=prompt.name,
                        path=prompt.path,
                        suggestion="Open with 'You are <role>.' Anthropic's guide shows that even a single-sentence persona meaningfully focuses behavior.",
                    )
                )
        return out


class PromptXmlStructureRule(Rule):
    id = "PROMPT008"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        min_chars = int(cfg.options.get("min_chars", 1500))
        out: list[Finding] = []
        for prompt in bundle.prompts:
            if prompt.char_count < min_chars:
                continue
            if _XML_TAG.search(prompt.text):
                continue
            out.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.PROMPT,
                    severity=Severity.INFO,
                    message=f"Prompt '{prompt.name}' is {prompt.char_count} chars but uses no XML structuring tags.",
                    where=prompt.name,
                    path=prompt.path,
                    suggestion="Wrap distinct sections in tags like <instructions>, <context>, <examples>, <input>. Anthropic's guide credits XML structuring with measurable parsing-accuracy gains on complex prompts.",
                    evidence={"chars": prompt.char_count},
                )
            )
        return out


class PromptExamplesRule(Rule):
    id = "PROMPT009"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        min_chars = int(cfg.options.get("min_chars", 1500))
        out: list[Finding] = []
        for prompt in bundle.prompts:
            if prompt.char_count < min_chars:
                continue
            if _EXAMPLE_TAG.search(prompt.text):
                continue
            if re.search(r"\bexample\b", prompt.text, re.IGNORECASE):
                continue
            out.append(
                Finding(
                    rule_id=self.id,
                    layer=Layer.PROMPT,
                    severity=Severity.INFO,
                    message=f"Prompt '{prompt.name}' is {prompt.char_count} chars but contains no examples.",
                    where=prompt.name,
                    path=prompt.path,
                    suggestion="Add 3–5 few-shot examples wrapped in <example> tags. Anthropic calls examples 'one of the most reliable ways to steer output'.",
                    evidence={"chars": prompt.char_count},
                )
            )
        return out


class PromptLongContextOrderRule(Rule):
    id = "PROMPT010"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        long_chars = int(cfg.options.get("min_chars", config.prompt_long_context_chars))
        out: list[Finding] = []
        for prompt in bundle.prompts:
            if prompt.char_count < long_chars:
                continue
            # Pick the last paragraph as a proxy for "the imperative/question".
            paras = [p.strip() for p in re.split(r"\n\s*\n", prompt.text) if p.strip()]
            if len(paras) < 3:
                continue
            tail = paras[-1].lower()
            head = "\n".join(paras[:3]).lower()
            tail_has_imperative = bool(re.search(r"\b(answer|analyze|extract|classify|summarize|write|generate|return|respond|produce|identify)\b", tail))
            head_has_imperative = bool(re.search(r"\b(answer|analyze|extract|classify|summarize|write|generate|return|respond|produce|identify)\b", head))
            if head_has_imperative and not tail_has_imperative:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.PROMPT,
                        severity=Severity.WARN,
                        message=f"Long prompt '{prompt.name}' ({prompt.char_count} chars) appears to ask the question near the top, not at the end.",
                        where=prompt.name,
                        path=prompt.path,
                        suggestion="For long-context prompts, put documents at the top and the imperative/question at the very end. Anthropic measures up to a 30% quality lift from this ordering.",
                        evidence={"chars": prompt.char_count},
                    )
                )
        return out
