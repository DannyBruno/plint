"""Pretty terminal output via rich."""

from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plint.core.findings import Finding, Report, Severity

_SEV_STYLE = {
    Severity.ERROR: "bold red",
    Severity.WARN: "yellow",
    Severity.INFO: "cyan",
}
_SEV_ICON = {
    Severity.ERROR: "✖",
    Severity.WARN: "⚠",
    Severity.INFO: "ℹ",
}


def _format_finding(f: Finding) -> Panel:
    style = _SEV_STYLE[f.severity]
    icon = _SEV_ICON[f.severity]
    header = Text()
    header.append(f"{icon} {f.severity.value.upper()} ", style=style)
    header.append(f"{f.rule_id}", style="bold")
    header.append(f"  {f.layer.value}  ")
    header.append(f.where, style="dim")

    body = Text()
    body.append(f.message + "\n")
    if f.path:
        body.append(f"  in {f.path}\n", style="dim")
    if f.suggestion:
        body.append("  → ", style="green")
        body.append(f.suggestion, style="green")
    return Panel(body, title=header, border_style=style, padding=(0, 1))


def write_text(report: Report, console: Console | None = None) -> None:
    console = console or Console()

    counts = report.summary.get("counts", {})
    console.print(
        f"[dim]Scanned[/dim] [bold]{counts.get('prompts', 0)}[/bold] prompts, "
        f"[bold]{counts.get('skills', 0)}[/bold] skills, "
        f"[bold]{counts.get('tools', 0)}[/bold] tools."
    )

    policy = report.summary.get("policy") or {}
    if policy.get("model") or policy.get("family"):
        model = policy.get("model") or "(unknown)"
        family = policy.get("family") or "generic"
        source = policy.get("source") or "default"
        overrides = policy.get("overrides") or {}
        suffix = ""
        if overrides:
            adjusted = [rid for rid, sev in overrides.items() if sev is not None]
            suppressed = [rid for rid, sev in overrides.items() if sev is None]
            bits = []
            if adjusted:
                bits.append(f"re-graded: {', '.join(adjusted)}")
            if suppressed:
                bits.append(f"suppressed: {', '.join(suppressed)}")
            suffix = f"  [dim]({'; '.join(bits)})[/dim]"
        console.print(
            f"[dim]Target:[/dim] [bold]{model}[/bold] "
            f"[dim](family={family}, via {source})[/dim]{suffix}"
        )
    elif policy.get("notes"):
        console.print(f"[dim]Target:[/dim] generic [dim]({policy['notes'][0]})[/dim]")

    if not report.findings:
        console.print("[green]✓ No findings.[/green]")
        return

    for f in report.findings:
        console.print(_format_finding(f))

    sev_counter = Counter(f.severity for f in report.findings)
    summary = Table.grid(padding=(0, 2))
    summary.add_column(justify="right")
    summary.add_column()
    for sev in [Severity.ERROR, Severity.WARN, Severity.INFO]:
        summary.add_row(
            Text(_SEV_ICON[sev], style=_SEV_STYLE[sev]),
            f"[{_SEV_STYLE[sev]}]{sev.value}[/]: {sev_counter.get(sev, 0)}",
        )
    console.print()
    console.print(summary)

    if report.summary.get("judge_ran") is False and "judge_error" in report.summary:
        console.print(f"\n[dim]Judge skipped: {report.summary['judge_error']}[/dim]")
