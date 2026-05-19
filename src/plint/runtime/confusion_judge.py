"""Runtime LLM-as-judge: examine the trace tail and look for systemic confusion patterns.

Surfaces things the deterministic detectors can't easily catch: the model giving up,
fabricating tool names, confusing user intent, repeatedly course-correcting, etc.
"""

from __future__ import annotations

import json
from typing import Any

from plint.core.config import Config
from plint.core.findings import Finding, Layer, Severity
from plint.runtime.trace import Trace
from plint.static.judge import _call_judge, _detect_provider, _parse

_SYSTEM = """You are reviewing a trace of an LLM agent's reasoning. Your job is to detect
whether the model knew what it was doing.

Look specifically for:

  - The model expressing confusion or apologizing for confusion
  - Tool-call sequences that don't match a coherent plan
  - The model fabricating capabilities or tool names
  - The model repeatedly re-explaining the same idea to itself
  - The model abandoning a chain of work without completing it
  - The model asking the user for information that was likely already in context

For each issue, output ONLY a JSON object with this shape:

{
  "findings": [
    {
      "rule_id": "RUNTIME-JUDGE-001",
      "severity": "info" | "warn" | "error",
      "message": "<one sentence describing what you saw>",
      "suggestion": "<one sentence, actionable for the developer>",
      "evidence": "<the specific snippet that triggered this>"
    }
  ]
}

If the trace looks coherent, return {"findings": []}. Do not include any other text."""


def _summarize_trace(trace: Trace) -> str:
    out: list[str] = []
    for i, call in enumerate(trace.calls):
        out.append(f"--- call {i + 1} (provider={call.provider}, model={call.model}) ---")
        if call.system:
            out.append("system: " + call.system[:600])
        for m in (call.messages or [])[-4:]:
            role = m.get("role", "?")
            content = m.get("content")
            if isinstance(content, str):
                snippet = content[:400]
            else:
                try:
                    snippet = json.dumps(content)[:400]
                except Exception:
                    snippet = str(content)[:400]
            out.append(f"  [{role}] {snippet}")
        if call.assistant_text:
            out.append("  assistant: " + call.assistant_text[:600])
        for t in call.tool_calls:
            out.append(f"  → tool {t.name}({json.dumps(t.arguments)[:200]})")
        if call.stop_reason:
            out.append(f"  stop_reason: {call.stop_reason}")
    return "\n".join(out)


def run_confusion_judge(trace: Trace, config: Config | None = None) -> list[Finding]:
    if not trace.calls:
        return []
    cfg = config or Config()
    provider, model = _detect_provider(cfg)
    raw = _call_judge(provider, model, _summarize_trace(trace))
    items = _parse(raw)

    findings: list[Finding] = []
    for i, item in enumerate(items):
        try:
            severity = Severity(item.get("severity", "warn"))
        except ValueError:
            severity = Severity.WARN
        rule_id = item.get("rule_id") or f"RUNTIME-JUDGE-{i + 1:03d}"
        evidence: dict[str, Any] = {"judge_model": f"{provider}/{model}"}
        if "evidence" in item:
            evidence["snippet"] = item["evidence"]
        findings.append(
            Finding(
                rule_id=rule_id,
                layer=Layer.RUNTIME,
                severity=severity,
                message=item.get("message", "(no message)"),
                where=item.get("where", "trace"),
                suggestion=item.get("suggestion"),
                evidence=evidence,
            )
        )
    return findings
