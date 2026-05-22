"""Configuration loading — .plint.toml or pyproject.toml [tool.plint]."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


@dataclass
class RuleConfig:
    enabled: bool = True
    severity: str | None = None  # override default severity
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    # Discovery
    prompt_globs: list[str] = field(default_factory=lambda: [
        "**/prompts/**/*.md",
        "**/prompts/**/*.txt",
        "**/*.prompt",
        "**/*.prompt.md",
    ])
    skill_globs: list[str] = field(default_factory=lambda: ["**/SKILL.md", "**/skills/**/*.md"])
    tool_globs: list[str] = field(default_factory=lambda: ["**/tools/**/*.json"])
    exclude_globs: list[str] = field(default_factory=lambda: [
        "**/node_modules/**",
        "**/.venv/**",
        "**/venv/**",
        "**/__pycache__/**",
        "**/.git/**",
    ])

    # Rule thresholds
    prompt_warn_lines: int = 200
    prompt_error_lines: int = 500
    prompt_long_context_chars: int = 20000
    tool_min_description_chars: int = 40
    tool_param_description_min_chars: int = 10
    skill_body_warn_lines: int = 500           # mgechev recommendation
    skill_body_error_words: int = 5000         # Anthropic recommendation
    skill_description_max_chars: int = 1024    # Anthropic frontmatter cap
    skill_script_warn_lines: int = 200         # strict mode only
    skill_subdir_max_depth: int = 1            # strict mode only

    # Opt-in strict mode (mgechev-style stricter rules)
    strict: bool = False

    # Model-aware policy (None = autodetect from bundle, or fall back to generic)
    target_model: str | None = None
    target_provider: str | None = None

    # Rule toggles (rule_id -> RuleConfig)
    rules: dict[str, RuleConfig] = field(default_factory=dict)

    # LLM judge
    judge_enabled: bool = True
    judge_provider: str | None = None  # auto-detect if None
    judge_model: str | None = None

    @classmethod
    def from_file(cls, path: Path) -> Config:
        with path.open("rb") as f:
            data = tomllib.load(f)
        if path.name == "pyproject.toml":
            data = data.get("tool", {}).get("plint", {})
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        cfg = cls()
        for k, v in data.items():
            if k == "rules" and isinstance(v, dict):
                cfg.rules = {
                    rid: RuleConfig(**rdata) if isinstance(rdata, dict) else RuleConfig(enabled=bool(rdata))
                    for rid, rdata in v.items()
                }
            elif hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    def rule(self, rule_id: str) -> RuleConfig:
        return self.rules.get(rule_id, RuleConfig())


def load_config(start: Path | None = None) -> Config:
    """Walk up from `start` looking for .plint.toml or pyproject.toml."""

    start = (start or Path.cwd()).resolve()
    for parent in [start, *start.parents]:
        plint_toml = parent / ".plint.toml"
        if plint_toml.exists():
            return Config.from_file(plint_toml)
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                if "tool" in data and "plint" in data["tool"]:
                    return Config.from_dict(data["tool"]["plint"])
            except Exception:
                continue
    return Config()
