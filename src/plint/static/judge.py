"""Static LLM-as-judge: cross-layer architecture audit.

Sends a compact summary of the prompts + skills + tools to a model and asks it to flag
misplaced logic. Auto-detects which provider to use based on available API keys.

Findings are emitted with rule_id "JUDGE001" .. "JUDGEnnn".
"""

from __future__ import annotations

import json
import os
from typing import Any

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity

_SYSTEM = """You are reviewing the architecture of an LLM agent. The agent has three layers:

  1. PROMPTS — persona + when to invoke skills. Should be SHORT.
  2. SKILLS — task-specific procedures the agent loads on demand. Procedural, recipe-like.
  3. TOOLS — atomic, deterministic capabilities. Single responsibility, clear description.

Common mistakes you should flag:

  - Multi-step procedures embedded in the base prompt (should be a skill)
  - Tools whose description encodes a workflow (should be several smaller tools + a skill)
  - Skills that are unstructured prose with no procedure (skill in disguise of a prompt)
  - Instructions duplicated across two layers (drift risk)
  - Deterministic operations described in prompts/skills that should be tools
  - Routing logic in skills that belongs in the prompt
  - Conditional logic inside tool descriptions that belongs in the model's reasoning

For each issue, output ONLY a JSON object with this shape:
{
  "findings": [
    {
      "rule_id": "JUDGE001",
      "layer": "prompt" | "skill" | "tool" | "cross",
      "severity": "info" | "warn" | "error",
      "where": "<artifact name>",
      "message": "<one sentence>",
      "suggestion": "<one sentence, actionable>"
    }
  ]
}

If you find no issues, output {"findings": []}. Do not include any other text."""


def _summarize(bundle: AgentBundle) -> str:
    out: list[str] = []
    out.append("=== PROMPTS ===")
    for p in bundle.prompts:
        out.append(f"--- prompt: {p.name} ({p.line_count} lines) ---")
        out.append(p.text[:6000])
    out.append("\n=== SKILLS ===")
    for s in bundle.skills:
        out.append(f"--- skill: {s.name} ---")
        out.append(f"description: {s.description}")
        out.append("body:")
        out.append(s.body[:4000])
    out.append("\n=== TOOLS ===")
    for t in bundle.tools:
        out.append(f"--- tool: {t.name} ---")
        out.append(f"description: {t.description}")
        try:
            out.append("parameters: " + json.dumps(t.parameters)[:1000])
        except Exception:
            pass
    return "\n".join(out)


def _detect_provider(cfg: Config) -> tuple[str, str]:
    """Return (provider, model) — honors config overrides, else auto-detects from env."""

    if cfg.judge_provider and cfg.judge_model:
        return cfg.judge_provider, cfg.judge_model
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic", cfg.judge_model or "claude-sonnet-4-6"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", cfg.judge_model or "gpt-5-mini"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter", cfg.judge_model or "anthropic/claude-sonnet-4-6"
    raise RuntimeError(
        "No LLM judge provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY, "
        "or pass --no-judge."
    )


def _call_judge(provider: str, model: str, prompt: str) -> str:
    if provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    if provider in ("openai", "openrouter"):
        from openai import OpenAI

        kwargs: dict[str, Any] = {}
        if provider == "openrouter":
            kwargs["base_url"] = "https://openrouter.ai/api/v1"
            kwargs["api_key"] = os.environ["OPENROUTER_API_KEY"]
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""
    raise ValueError(f"Unknown judge provider: {provider}")


def _parse(raw: str) -> list[dict[str, Any]]:
    raw = raw.strip()
    # Strip ```json fences if present.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
        else:
            return []
    findings = data.get("findings") if isinstance(data, dict) else None
    return findings if isinstance(findings, list) else []


def run_judge(bundle: AgentBundle, config: Config) -> list[Finding]:
    if bundle.is_empty():
        return []
    provider, model = _detect_provider(config)
    summary = _summarize(bundle)
    raw = _call_judge(provider, model, summary)
    items = _parse(raw)

    out: list[Finding] = []
    for i, item in enumerate(items):
        try:
            layer = Layer(item.get("layer", "cross"))
        except ValueError:
            layer = Layer.CROSS
        try:
            severity = Severity(item.get("severity", "warn"))
        except ValueError:
            severity = Severity.WARN
        rule_id = item.get("rule_id") or f"JUDGE{i + 1:03d}"
        out.append(
            Finding(
                rule_id=rule_id,
                layer=layer,
                severity=severity,
                message=item.get("message", "(no message)"),
                where=item.get("where", "judge"),
                suggestion=item.get("suggestion"),
                evidence={"judge_model": f"{provider}/{model}"},
            )
        )
    return out
