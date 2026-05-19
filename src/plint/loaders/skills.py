"""Load Anthropic-style SKILL.md files.

Expected shape:
    ---
    name: my-skill
    description: Use this when…
    ---
    # Skill body
    1. Step one
    2. Step two
"""

from __future__ import annotations

from pathlib import Path

from plint.core.artifacts import Skill
from plint.loaders._frontmatter import split_frontmatter


def load_skill_file(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    name = fm.get("name") or path.parent.name if path.name == "SKILL.md" else (fm.get("name") or path.stem)
    description = fm.get("description", "")
    return Skill(name=name, description=description, body=body, path=path, frontmatter=fm)
