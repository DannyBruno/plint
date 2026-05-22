"""plint command-line interface."""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from plint.core.config import load_config
from plint.report import write_json, write_sarif, write_text
from plint.static.analyzer import analyze

app = typer.Typer(
    help="Static and runtime linter for agent prompts, skills, and tool definitions.",
    no_args_is_help=True,
    add_completion=False,
)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    sarif = "sarif"


@app.command("analyze")
def analyze_cmd(
    path: Path = typer.Argument(Path("."), help="Project directory to scan."),
    fmt: OutputFormat = typer.Option(OutputFormat.text, "--format", "-f", help="Output format."),
    judge: bool = typer.Option(True, "--judge/--no-judge", help="Run the LLM-as-judge cross-layer pass."),
    strict: bool = typer.Option(False, "--strict/--no-strict", help="Enable opinionated stricter rules (script size caps, single-level subdirs, etc)."),
    model: Optional[str] = typer.Option(None, "--model", help="Target model name (e.g. claude-opus-4-7, gpt-5.5, gpt-5-mini). Enables per-family policy. Autodetected from tools/frontmatter if omitted."),
    fail_on: str = typer.Option(
        "error",
        "--fail-on",
        help="Exit non-zero when at least one finding matches this severity ('error', 'warn', 'info', or 'none').",
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write to a file instead of stdout."),
) -> None:
    """Statically analyze prompts/skills/tools in PATH."""

    console = Console(stderr=(fmt is not OutputFormat.text))
    cfg = load_config(path)
    if strict:
        cfg.strict = True
    if model:
        cfg.target_model = model
    report = analyze(path, cfg, use_judge=judge)

    stream = output.open("w", encoding="utf-8") if output else None
    try:
        if fmt is OutputFormat.text:
            write_text(report, console=Console(file=stream) if stream else console)
        elif fmt is OutputFormat.json:
            write_json(report, stream=stream or sys.stdout)
        elif fmt is OutputFormat.sarif:
            write_sarif(report, stream=stream or sys.stdout)
    finally:
        if stream:
            stream.close()

    code = _exit_code(report, fail_on)
    if code:
        raise typer.Exit(code=code)


@app.command("rules")
def rules_cmd() -> None:
    """List all built-in static rules."""

    from plint.static.heuristics import ALL_RULES

    console = Console()
    for r in ALL_RULES:
        console.print(f"[bold]{r.id}[/]  [dim]{r.__class__.__name__}[/]")


def _exit_code(report, fail_on: str) -> int:
    fail_on = fail_on.lower()
    if fail_on == "none":
        return 0
    levels = {"info": 1, "warn": 2, "error": 3}
    threshold = levels.get(fail_on, 3)
    for f in report.findings:
        if levels.get(f.severity.value, 0) >= threshold:
            return 1
    return 0


if __name__ == "__main__":
    app()
