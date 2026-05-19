"""Additional tool quality rules grounded in the towardsai tool-writing guide.

  TOOL003 — description has no example invocations
  TOOL004 — description lacks 'use when' / when-to-invoke phrasing
  TOOL005 — parameter missing a description (model has nothing to go on)
  TOOL006 — parameter type missing entirely
"""

from __future__ import annotations

import re

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.static.heuristics._base import Rule

_EXAMPLE = re.compile(r"(?:^|\b)(?:example|e\.g\.|for example|sample|usage)[\s:]", re.IGNORECASE)
_INVOCATION = re.compile(r"\b[a-z_][a-z0-9_]*\s*\([^)]{0,160}\)", re.IGNORECASE)
_WHEN_PHRASES = [
    re.compile(r"\buse (this|when|for|to)\b", re.IGNORECASE),
    re.compile(r"\bcall (this|when)\b", re.IGNORECASE),
    re.compile(r"\bused (to|for|when)\b", re.IGNORECASE),
    re.compile(r"\buseful (when|for|to)\b", re.IGNORECASE),
    re.compile(r"\binvoke (this|when)\b", re.IGNORECASE),
]


class ToolExampleRule(Rule):
    id = "TOOL003"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for tool in bundle.tools:
            desc = tool.description or ""
            if not desc:
                continue
            has_example_word = bool(_EXAMPLE.search(desc))
            has_invocation = bool(_INVOCATION.search(desc))
            if not (has_example_word or has_invocation):
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.TOOL,
                        severity=Severity.INFO,
                        message=f"Tool '{tool.name}' description has no example invocation.",
                        where=tool.name,
                        path=tool.path,
                        suggestion="Add 1–2 short examples like `Example: tool_name(arg='value')`. Concrete examples meaningfully improve tool-call accuracy.",
                        evidence={"description_chars": len(desc)},
                    )
                )
        return out


class ToolUseWhenRule(Rule):
    id = "TOOL004"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for tool in bundle.tools:
            desc = tool.description or ""
            if not desc:
                continue
            if not any(p.search(desc) for p in _WHEN_PHRASES):
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.TOOL,
                        severity=Severity.INFO,
                        message=f"Tool '{tool.name}' description doesn't say *when* to call it.",
                        where=tool.name,
                        path=tool.path,
                        suggestion="Add 'Use this when…' or 'Call this to…'. The model picks tools by matching the user's intent against this text.",
                        evidence={"description": desc[:200]},
                    )
                )
        return out


class ToolParamDescriptionRule(Rule):
    id = "TOOL005"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        min_chars = int(cfg.options.get("min_description_chars", config.tool_param_description_min_chars))
        out: list[Finding] = []
        for tool in bundle.tools:
            params = tool.parameters if isinstance(tool.parameters, dict) else {}
            props = params.get("properties", {})
            if not isinstance(props, dict) or not props:
                continue
            missing: list[str] = []
            shallow: list[str] = []
            for pname, spec in props.items():
                if not isinstance(spec, dict):
                    continue
                desc = spec.get("description")
                if not desc:
                    missing.append(pname)
                elif isinstance(desc, str) and len(desc.strip()) < min_chars:
                    shallow.append(pname)
            triggers = []
            if missing:
                triggers.append(f"missing description: {', '.join(missing)}")
            if shallow:
                triggers.append(f"description <{min_chars} chars: {', '.join(shallow)}")
            if triggers:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.TOOL,
                        severity=Severity.WARN,
                        message=f"Tool '{tool.name}' has parameters with weak documentation ({'; '.join(triggers)}).",
                        where=tool.name,
                        path=tool.path,
                        suggestion="Every parameter needs a description. The model uses these to decide what to put in each field.",
                        evidence={"missing": missing, "shallow": shallow},
                    )
                )
        return out


class ToolParamTypeRule(Rule):
    id = "TOOL006"

    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]:
        cfg = config.rule(self.id)
        if not cfg.enabled:
            return []
        out: list[Finding] = []
        for tool in bundle.tools:
            params = tool.parameters if isinstance(tool.parameters, dict) else {}
            props = params.get("properties", {})
            if not isinstance(props, dict) or not props:
                continue
            offenders: list[str] = []
            for pname, spec in props.items():
                if not isinstance(spec, dict):
                    continue
                t = spec.get("type")
                # An unspecified type or a bare "object" / "array" with no shape is a smell.
                if not t:
                    offenders.append(pname)
                elif t == "object" and not spec.get("properties") and not spec.get("additionalProperties"):
                    offenders.append(f"{pname} (open-ended object)")
                elif t == "array" and not spec.get("items"):
                    offenders.append(f"{pname} (untyped array)")
            if offenders:
                out.append(
                    Finding(
                        rule_id=self.id,
                        layer=Layer.TOOL,
                        severity=Severity.WARN,
                        message=f"Tool '{tool.name}' parameters lack a concrete type: {', '.join(offenders)}.",
                        where=tool.name,
                        path=tool.path,
                        suggestion="Give every parameter an explicit JSON Schema type, including `items` for arrays and `properties` for objects.",
                        evidence={"offenders": offenders},
                    )
                )
        return out
