"""Model-aware policy.

Adjusts rule severity based on the target model family. Detection precedence:

  1. Explicit `target_model` in Config (or `--model` on CLI).
  2. `target_model:` / `model:` field in a prompt's YAML frontmatter.
  3. Provider inferred from tool format (OpenAI-shape → gpt-5.5; Anthropic-shape → claude-opus-4-7).
  4. None — no overrides applied.

Every override here traces back to a cited source in the README. The general shape:

  * Modern models (Claude 4.6+, GPT-5.5+) — bump emphasis-on-emphasis warnings, since both
    Anthropic and OpenAI explicitly say `MUST`/`CRITICAL`/`ALWAYS` cause overtriggering.
  * Small/literal models (gpt-5-mini, gpt-5-nano) — disable rules that flag scaffolding,
    since these models actually benefit from explicit process and emphasis.
  * Codex models — strengthen the rule against process-heavy prompts (no upfront plans).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Severity

# --- family detection -------------------------------------------------------

_GPT_CODEX = re.compile(r"\b(codex|gpt-[0-9.]+-codex)\b", re.IGNORECASE)
_GPT_MINI_NANO = re.compile(r"gpt-[0-9.]+-(mini|nano)\b", re.IGNORECASE)
_GPT_55 = re.compile(r"gpt-5[.-]5\b", re.IGNORECASE)
_GPT_5 = re.compile(r"gpt-5(?![.-]?[0-9])", re.IGNORECASE)
_CLAUDE_46_PLUS = re.compile(
    r"claude-(?:opus|sonnet|haiku)-(?:4-[6-9]|[5-9])\b", re.IGNORECASE
)
_CLAUDE_LEGACY = re.compile(r"claude-(?:1|2|3|instant)\b", re.IGNORECASE)
_CLAUDE_GENERIC = re.compile(r"\bclaude\b", re.IGNORECASE)


def family_for(model: str | None) -> str | None:
    """Return a coarse family identifier for a model string."""

    if not model:
        return None
    if _GPT_CODEX.search(model):
        return "gpt-codex"
    if _GPT_MINI_NANO.search(model):
        return "gpt-mini"
    if _GPT_55.search(model):
        return "gpt-5.5"
    if _GPT_5.search(model):
        return "gpt-5"
    if _CLAUDE_46_PLUS.search(model):
        return "claude-4.6+"
    if _CLAUDE_LEGACY.search(model):
        return "claude-legacy"
    if _CLAUDE_GENERIC.search(model):
        return "claude"
    return None


def _provider_for_family(family: str | None) -> str | None:
    if family and family.startswith("claude"):
        return "anthropic"
    if family and family.startswith("gpt"):
        return "openai"
    return None


# --- per-family policy table ------------------------------------------------
# A value of `None` means "suppress this rule entirely".
# A `Severity` value overrides the rule's default severity.

_POLICY_TABLE: dict[str, dict[str, Optional[Severity]]] = {
    "claude-4.6+": {
        # Anthropic prompting guide: aggressive emphasis overtriggers on 4.6+ models.
        "PROMPT005": Severity.WARN,
        # Anthropic prompting guide explicitly emphasises XML structuring.
        "PROMPT008": Severity.WARN,
    },
    "claude": {
        # Generic Claude — treat as modern unless we know otherwise.
        "PROMPT005": Severity.WARN,
        "PROMPT008": Severity.WARN,
    },
    "claude-legacy": {
        # Pre-4.6 models historically needed/tolerated stronger emphasis.
        "PROMPT005": None,
    },
    "gpt-5.5": {
        # OpenAI guide: avoid MUST/NEVER/ALWAYS for judgment calls.
        "PROMPT005": Severity.WARN,
        # OpenAI doesn't require XML structuring.
        "PROMPT008": None,
        # GPT-5.5 strongly prefers outcome-first over process-heavy prompts.
        "PROMPT003": Severity.WARN,
    },
    "gpt-5": {
        "PROMPT005": Severity.INFO,
        "PROMPT008": None,
    },
    "gpt-mini": {
        # Small/literal models — they need scaffolding and emphasis.
        "PROMPT005": None,
        "PROMPT003": None,
        "PROMPT008": Severity.INFO,
    },
    "gpt-codex": {
        # Codex guide: no upfront plans or preambles.
        "PROMPT003": Severity.WARN,
        "PROMPT008": None,
    },
}


# --- ModelPolicy dataclass --------------------------------------------------


@dataclass
class ModelPolicy:
    model: str | None = None
    provider: str | None = None
    family: str | None = None
    source: str = "default"   # "config" | "frontmatter" | "tools" | "default"
    severity_overrides: dict[str, Optional[Severity]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def adjust(self, finding: Finding) -> Finding | None:
        """Apply policy to a finding. Return None to suppress; otherwise return a (possibly re-graded) finding."""

        if finding.rule_id not in self.severity_overrides:
            return finding
        override = self.severity_overrides[finding.rule_id]
        if override is None:
            return None
        if override == finding.severity:
            return finding
        return Finding(
            rule_id=finding.rule_id,
            layer=finding.layer,
            severity=override,
            message=finding.message,
            where=finding.where,
            path=finding.path,
            line=finding.line,
            suggestion=finding.suggestion,
            evidence={**finding.evidence, "_policy_adjusted": True, "_target": f"{self.provider}/{self.model}"},
        )

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "provider": self.provider,
            "family": self.family,
            "source": self.source,
            "overrides": {k: (v.value if v is not None else None) for k, v in self.severity_overrides.items()},
            "notes": list(self.notes),
        }


# --- detection --------------------------------------------------------------


_DEFAULT_MODEL_PER_PROVIDER = {
    "anthropic": "claude-opus-4-7",
    "openai": "gpt-5.5",
}


def _policy_for(family: str | None) -> dict[str, Optional[Severity]]:
    return dict(_POLICY_TABLE.get(family or "", {}))


def detect_model_policy(bundle: AgentBundle, config: Config) -> ModelPolicy:
    # 1. Explicit config / CLI
    if config.target_model:
        family = family_for(config.target_model)
        return ModelPolicy(
            model=config.target_model,
            provider=config.target_provider or _provider_for_family(family),
            family=family,
            source="config",
            severity_overrides=_policy_for(family),
            notes=[f"Target model set in config: {config.target_model}"],
        )

    # 2. Prompt frontmatter
    for prompt in bundle.prompts:
        decl = prompt.metadata.get("target_model") or prompt.metadata.get("model")
        if isinstance(decl, str) and decl.strip():
            family = family_for(decl)
            return ModelPolicy(
                model=decl,
                provider=config.target_provider or _provider_for_family(family),
                family=family,
                source="frontmatter",
                severity_overrides=_policy_for(family),
                notes=[f"Target model declared in prompt frontmatter '{prompt.name}': {decl}"],
            )

    # 3. Inferred from tool format majority
    provider_counts: dict[str, int] = {}
    for tool in bundle.tools:
        if tool.provider and tool.provider != "unknown":
            provider_counts[tool.provider] = provider_counts.get(tool.provider, 0) + 1
    if provider_counts:
        inferred = max(provider_counts, key=lambda k: provider_counts[k])
        default_model = _DEFAULT_MODEL_PER_PROVIDER.get(inferred)
        family = family_for(default_model)
        return ModelPolicy(
            model=default_model,
            provider=inferred,
            family=family,
            source="tools",
            severity_overrides=_policy_for(family),
            notes=[f"Provider inferred from tool format: {inferred}; defaulted to {default_model}"],
        )

    # 4. Nothing detected
    return ModelPolicy(
        source="default",
        notes=["No target model detected. Set `target_model` in .plint.toml or `--model` to enable per-family policy."],
    )
