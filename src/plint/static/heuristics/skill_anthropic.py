"""Skill rules grounded in Anthropic's official skills guide + mgechev/skills-best-practices.

Adds:
  SKILL004 — name doesn't match folder name
  SKILL005 — description exceeds 1024 chars (Anthropic hard cap)
  SKILL006 — name uses reserved prefix `claude` / `anthropic`
  SKILL007 — frontmatter contains `<` or `>` (Anthropic security restriction)
  SKILL008 — README.md / CHANGELOG.md / INSTALLATION_GUIDE.md inside skill folder
  SKILL009 — name not kebab-case `^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$`
  SKILL010 — body too large (lines warn / words error)
  SKILL011 — description has no negative trigger (INFO)
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_KEBAB = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")
_RESERVED_PREFIX = re.compile(r"^(claude|anthropic)([-_]|$)", re.IGNORECASE)
_DISALLOWED_FILES = {
    "README.md",
    "README",
    "CHANGELOG.md",
    "CHANGELOG",
    "INSTALLATION_GUIDE.md",
    "INSTALL.md",
    "CONTRIBUTING.md",
    "HISTORY.md",
}
_NEGATIVE_TRIGGER = re.compile(r"\b(do not|don'?t)\s+use\b", re.IGNORECASE)


class SkillNameFolderRule(Rule):
    id = "SKILL004"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            folder = skill.folder
            if folder is None or skill.path is None:
                continue
            # Only enforce when the skill lives in its own folder named after it
            # (i.e. when the file is SKILL.md). Bare *.md files in skills/ get a pass.
            if skill.path.name != "SKILL.md":
                continue
            declared = (skill.frontmatter.get("name") or "").strip()
            if declared and declared != folder.name:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.WARN,
                        message=f"Skill name '{declared}' doesn't match folder name '{folder.name}'.",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Anthropic's skills guide requires the `name` frontmatter to match the folder name (both kebab-case).",
                        evidence={"name": declared, "folder": folder.name},
                    )
                )
        return out


class SkillDescriptionLengthRule(Rule):
    id = "SKILL005"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        cap = int(cfg.options.get("max_chars", config.skill_description_max_chars))
        out: list[Finding] = []
        for skill in bundle.skills:
            desc = skill.description or ""
            if len(desc) > cap:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.ERROR,
                        message=f"Skill '{skill.name}' description is {len(desc)} chars (Anthropic cap is {cap}).",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Move detail out of `description` and into the SKILL.md body or `references/`. The description should be a one-line trigger.",
                        evidence={"chars": len(desc), "cap": cap},
                    )
                )
        return out


class SkillReservedPrefixRule(Rule):
    id = "SKILL006"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            name = (skill.frontmatter.get("name") or skill.name or "").strip()
            if _RESERVED_PREFIX.match(name):
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.ERROR,
                        message=f"Skill name '{name}' starts with a reserved prefix (`claude` / `anthropic`).",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Rename the skill — Anthropic reserves these prefixes.",
                    )
                )
        return out


class SkillFrontmatterXmlRule(Rule):
    id = "SKILL007"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            for k, v in (skill.frontmatter or {}).items():
                if isinstance(v, str) and ("<" in v or ">" in v):
                    out.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.SKILL,
                            severity=Severity.ERROR,
                            message=f"Skill '{skill.name}' frontmatter field '{k}' contains XML angle brackets — Anthropic forbids this for security reasons.",
                            where=skill.name,
                            path=skill.path,
                            suggestion="Remove `<` and `>` from frontmatter. They could otherwise inject instructions into the system prompt.",
                            evidence={"field": k, "value": v[:120]},
                        )
                    )
                    break
        return out


class SkillForbiddenFilesRule(Rule):
    id = "SKILL008"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            folder = skill.folder
            if folder is None or skill.path is None or skill.path.name != "SKILL.md":
                continue
            for entry in folder.iterdir():
                if entry.is_file() and entry.name in _DISALLOWED_FILES:
                    out.append(
                        Finding(
                            rule_id=self.id,
                            layer=Layer.SKILL,
                            severity=Severity.WARN,
                            message=f"Skill '{skill.name}' contains a human-facing doc file '{entry.name}' — Anthropic recommends keeping skill folders clean.",
                            where=skill.name,
                            path=entry,
                            suggestion="Move repo-level docs (README/CHANGELOG) up out of the skill folder. Skill content belongs in SKILL.md or `references/`.",
                            evidence={"file": entry.name},
                        )
                    )
        return out


class SkillKebabCaseRule(Rule):
    id = "SKILL009"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            name = (skill.frontmatter.get("name") or "").strip()
            if not name:
                continue
            if not _KEBAB.match(name):
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.WARN,
                        message=f"Skill name '{name}' is not kebab-case (lowercase, hyphens, 1–64 chars).",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Use kebab-case like `onboard-client`. No spaces, capitals, or underscores.",
                        evidence={"name": name},
                    )
                )
        return out


class SkillBodySizeRule(Rule):
    id = "SKILL010"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        warn_lines = int(cfg.options.get("warn_lines", config.skill_body_warn_lines))
        error_words = int(cfg.options.get("error_words", config.skill_body_error_words))
        out: list[Finding] = []
        for skill in bundle.skills:
            lines = len(skill.body_lines)
            words = skill.body_word_count
            if words >= error_words:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.ERROR,
                        message=f"Skill '{skill.name}' body is {words} words — exceeds Anthropic's ~{error_words}-word guidance.",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Move reference material into `references/` and link to it. Skills load on demand — bloated bodies waste context for every invocation.",
                        evidence={"words": words, "lines": lines, "error_words": error_words},
                    )
                )
            elif lines >= warn_lines:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.WARN,
                        message=f"Skill '{skill.name}' body is {lines} lines — past the {warn_lines}-line recommendation.",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Split into a thin SKILL.md plus `references/*.md` files, loaded only when the procedure needs them.",
                        evidence={"lines": lines, "warn_lines": warn_lines},
                    )
                )
        return out


class SkillNegativeTriggerRule(Rule):
    id = "SKILL011"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for skill in bundle.skills:
            desc = skill.description or ""
            if not desc:
                continue
            if not _NEGATIVE_TRIGGER.search(desc):
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.SKILL,
                        severity=Severity.INFO,
                        message=f"Skill '{skill.name}' description has no negative trigger (e.g. 'Do NOT use for…').",
                        where=skill.name,
                        path=skill.path,
                        suggestion="Add a 'Do NOT use for X' clause to the description. Helps Claude avoid loading the skill on related-but-wrong queries.",
                        evidence={"description": desc[:200]},
                    )
                )
        return out
