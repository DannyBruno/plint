"""Load prompt files (.md, .txt, .prompt, .prompt.md). Optional YAML frontmatter."""

from __future__ import annotations

from pathlib import Path

from plint.core.artifacts import Prompt
from plint.loaders._frontmatter import split_frontmatter


def load_prompt_file(path: Path) -> Prompt:
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    name = fm.get("name") or path.stem
    role = fm.get("role", "system")
    return Prompt(name=name, text=body, path=path, role=role, metadata=fm)
