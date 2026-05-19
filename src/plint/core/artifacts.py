"""Provider-agnostic representations of the three agent layers: prompts, skills, tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Prompt:
    """A system or developer prompt — text the model sees on every turn."""

    name: str
    text: str
    path: Path | None = None
    role: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass
class Skill:
    """An Anthropic-style skill: SKILL.md with YAML frontmatter + procedural body."""

    name: str
    description: str
    body: str
    path: Path | None = None
    frontmatter: dict[str, Any] = field(default_factory=dict)

    @property
    def body_lines(self) -> list[str]:
        return self.body.splitlines()

    @property
    def body_word_count(self) -> int:
        return len(self.body.split())

    @property
    def folder(self) -> Path | None:
        return self.path.parent if self.path else None


@dataclass
class Tool:
    """A tool/function definition — provider-normalized."""

    name: str
    description: str
    parameters: dict[str, Any]
    path: Path | None = None
    provider: str = "unknown"  # "anthropic" | "openai" | "openrouter"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentBundle:
    """The set of artifacts that make up one agent, discovered by a loader."""

    prompts: list[Prompt] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
    root: Path | None = None

    def is_empty(self) -> bool:
        return not (self.prompts or self.skills or self.tools)

    def counts(self) -> dict[str, int]:
        return {
            "prompts": len(self.prompts),
            "skills": len(self.skills),
            "tools": len(self.tools),
        }
