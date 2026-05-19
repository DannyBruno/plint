"""Strict-mode skill rules (mgechev/skills-best-practices).

These are stricter than Anthropic's official guidance. Disabled unless
`cfg.strict` is True (set via `plint analyze --strict` or `[tool.plint] strict = true`).

  SKILL101 — subdirectories deeper than one level
  SKILL102 — scripts/ files exceed configured line cap
  SKILL103 — scripts/ files import non-stdlib packages
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_IMPORT = re.compile(r"^\s*(?:from\s+([a-zA-Z_][\w.]*)|import\s+([a-zA-Z_][\w.]*))", re.MULTILINE)

# Best-effort stdlib detection. Python 3.10+ has sys.stdlib_module_names.
_STDLIB: set[str] = set(getattr(sys, "stdlib_module_names", set()))


class SkillSubdirDepthRule(Rule):
    id = "SKILL101"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        if not config.strict:
            return []
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        max_depth = int(cfg.options.get("max_depth", config.skill_subdir_max_depth))
        out: list[Finding] = []
        for skill in bundle.skills:
            folder = skill.folder
            if folder is None or skill.path is None or skill.path.name != "SKILL.md":
                continue
            for entry in folder.rglob("*"):
                if not entry.is_file():
                    continue
                rel_parts = entry.relative_to(folder).parts
                if len(rel_parts) > max_depth + 1:
                    out.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.SKILL,
                            severity=Severity.WARN,
                            message=f"Skill '{skill.name}' nests files deeper than {max_depth} level(s): {'/'.join(rel_parts)}.",
                            where=skill.name,
                            path=entry,
                            suggestion="Flatten the layout. Skill folders should be at most `scripts/foo.py` deep, not `scripts/utils/db/foo.py`.",
                            evidence={"depth": len(rel_parts) - 1, "max_depth": max_depth},
                        )
                    )
                    break
        return out


class SkillScriptSizeRule(Rule):
    id = "SKILL102"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        if not config.strict:
            return []
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        cap = int(cfg.options.get("warn_lines", config.skill_script_warn_lines))
        out: list[Finding] = []
        for skill in bundle.skills:
            folder = skill.folder
            if folder is None or skill.path is None or skill.path.name != "SKILL.md":
                continue
            scripts_dir = folder / "scripts"
            if not scripts_dir.exists():
                continue
            for entry in scripts_dir.rglob("*"):
                if not entry.is_file() or entry.suffix not in {".py", ".sh", ".js", ".ts"}:
                    continue
                try:
                    n = sum(1 for _ in entry.open("r", encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
                if n > cap:
                    out.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.SKILL,
                            severity=Severity.WARN,
                            message=f"Skill '{skill.name}' script '{entry.name}' is {n} lines (>{cap}).",
                            where=skill.name,
                            path=entry,
                            suggestion="Skill scripts should be tiny and single-purpose. Larger helpers belong in a regular library, not in a skill bundle.",
                            evidence={"lines": n, "cap": cap},
                        )
                    )
        return out


class SkillScriptImportsRule(Rule):
    id = "SKILL103"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        if not config.strict:
            return []
        cfg = config.rule(self.id)
        if not cfg.enabled or not _STDLIB:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            folder = skill.folder
            if folder is None or skill.path is None or skill.path.name != "SKILL.md":
                continue
            scripts_dir = folder / "scripts"
            if not scripts_dir.exists():
                continue
            for entry in scripts_dir.rglob("*.py"):
                if not entry.is_file():
                    continue
                try:
                    text = entry.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                non_stdlib: set[str] = set()
                for m in _IMPORT.finditer(text):
                    mod = (m.group(1) or m.group(2) or "").split(".")[0]
                    if mod and mod not in _STDLIB and not _is_local(folder, mod):
                        non_stdlib.add(mod)
                if non_stdlib:
                    out.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.SKILL,
                            severity=Severity.INFO,
                            message=f"Skill '{skill.name}' script '{entry.name}' imports non-stdlib modules: {', '.join(sorted(non_stdlib))}.",
                            where=skill.name,
                            path=entry,
                            suggestion="Skill scripts should rely on the stdlib so they run anywhere the skill is loaded. Vendor or remove third-party dependencies.",
                            evidence={"non_stdlib": sorted(non_stdlib)},
                        )
                    )
        return out


def _is_local(folder: Path, module: str) -> bool:
    return (folder / "scripts" / f"{module}.py").exists() or (folder / "scripts" / module).is_dir()
