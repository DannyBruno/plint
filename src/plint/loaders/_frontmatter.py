"""Parse YAML frontmatter (--- ... ---) from a text file."""

from __future__ import annotations

from typing import Any

import yaml


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Empty dict if no frontmatter present."""

    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if len(lines) < 2:
        return {}, text
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text
    fm_text = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1 :])
    try:
        fm = yaml.safe_load(fm_text) or {}
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}
    return fm, body
