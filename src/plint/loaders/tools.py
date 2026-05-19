"""Load tool/function definitions from JSON files.

Accepts:
    - OpenAI shape: {"type": "function", "function": {"name", "description", "parameters"}}
    - Anthropic shape: {"name", "description", "input_schema"}
    - Bare custom shape: {"name", "description", "parameters"}
    - Lists of any of the above.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from plint.core.artifacts import Tool


def _normalize(obj: dict[str, Any], path: Path) -> Tool | None:
    if "function" in obj and isinstance(obj["function"], dict):
        fn = obj["function"]
        return Tool(
            name=fn.get("name", ""),
            description=fn.get("description", ""),
            parameters=fn.get("parameters", {}),
            path=path,
            provider="openai",
            raw=obj,
        )
    if "input_schema" in obj:
        return Tool(
            name=obj.get("name", ""),
            description=obj.get("description", ""),
            parameters=obj.get("input_schema", {}),
            path=path,
            provider="anthropic",
            raw=obj,
        )
    if "name" in obj and ("parameters" in obj or "description" in obj):
        return Tool(
            name=obj.get("name", ""),
            description=obj.get("description", ""),
            parameters=obj.get("parameters", {}),
            path=path,
            provider="unknown",
            raw=obj,
        )
    return None


def load_tool_file(path: Path) -> list[Tool]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    tools: list[Tool] = []
    items = data if isinstance(data, list) else [data]
    for item in items:
        if isinstance(item, dict):
            tool = _normalize(item, path)
            if tool is not None:
                tools.append(tool)
    return tools
