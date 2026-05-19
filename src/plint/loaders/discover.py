"""Walk a project root and collect prompts, skills, tools into an AgentBundle."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.loaders.prompts import load_prompt_file
from plint.loaders.skills import load_skill_file
from plint.loaders.tools import load_tool_file


def _excluded(path: Path, patterns: list[str]) -> bool:
    s = str(path)
    return any(fnmatch(s, p) for p in patterns)


def _glob_files(root: Path, patterns: list[str], excludes: list[str]) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        for p in root.glob(pattern):
            if p.is_file() and not _excluded(p, excludes):
                found.add(p.resolve())
    return sorted(found)


def discover_bundle(root: Path, config: Config | None = None) -> AgentBundle:
    config = config or Config()
    root = root.resolve()

    bundle = AgentBundle(root=root)

    skill_paths = _glob_files(root, config.skill_globs, config.exclude_globs)
    skill_path_set = set(skill_paths)
    for p in skill_paths:
        try:
            bundle.skills.append(load_skill_file(p))
        except Exception:
            continue

    for p in _glob_files(root, config.prompt_globs, config.exclude_globs):
        if p in skill_path_set:
            continue
        try:
            bundle.prompts.append(load_prompt_file(p))
        except Exception:
            continue

    for p in _glob_files(root, config.tool_globs, config.exclude_globs):
        try:
            bundle.tools.extend(load_tool_file(p))
        except Exception:
            continue

    return bundle
