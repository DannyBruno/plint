"""High-level static analysis entry point."""

from __future__ import annotations

from pathlib import Path

from plint.core.artifacts import AgentBundle
from plint.core.config import Config, load_config
from plint.core.findings import Report
from plint.loaders.discover import discover_bundle
from plint.static.heuristics import ALL_RULES


def analyze(
    path: str | Path,
    config: Config | None = None,
    *,
    use_judge: bool | None = None,
) -> Report:
    """Run static analysis on a project directory.

    Args:
        path: Project root to scan.
        config: Optional config; if not provided, walks up from `path` looking for
                .plint.toml or pyproject.toml [tool.plint].
        use_judge: Force-enable or force-disable the LLM-as-judge pass. If None, uses
                config.judge_enabled.
    """

    root = Path(path).resolve()
    cfg = config or load_config(root)

    bundle = discover_bundle(root, cfg)
    report = Report()
    report.summary["root"] = str(root)
    report.summary["counts"] = bundle.counts()

    if bundle.is_empty():
        return report

    for rule in ALL_RULES:
        try:
            report.extend(rule.check(bundle, cfg))
        except Exception as exc:  # pragma: no cover
            report.summary.setdefault("rule_errors", []).append({"rule": rule.id, "error": str(exc)})

    judge_on = use_judge if use_judge is not None else cfg.judge_enabled
    if judge_on:
        try:
            from plint.static.judge import run_judge

            judge_findings = run_judge(bundle, cfg)
            report.extend(judge_findings)
            report.summary["judge_ran"] = True
        except Exception as exc:
            report.summary["judge_ran"] = False
            report.summary["judge_error"] = str(exc)
    else:
        report.summary["judge_ran"] = False

    report.summary["finding_count"] = len(report.findings)
    return report


def analyze_bundle(bundle: AgentBundle, config: Config | None = None) -> Report:
    """Run the heuristic rules over an already-loaded bundle (no judge)."""

    cfg = config or Config()
    report = Report()
    report.summary["counts"] = bundle.counts()
    for rule in ALL_RULES:
        report.extend(rule.check(bundle, cfg))
    report.summary["finding_count"] = len(report.findings)
    return report
