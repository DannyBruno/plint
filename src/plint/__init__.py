"""plint — Static and runtime linter for agent prompts, skills, and tool definitions.

Public API:
    plint.analyze(path)              run static analysis on a project directory
    plint.instrument()               monkey-patch installed Anthropic + OpenAI clients
    plint.uninstrument()             restore originals
    plint.session()                  context manager that records calls and reports findings
    plint.watch(...)                 decorator equivalent of session() around a function
"""

from plint.core.config import Config, load_config
from plint.core.findings import Finding, Severity
from plint.runtime.instrument import instrument, uninstrument
from plint.runtime.session import Session, session, watch
from plint.static.analyzer import analyze

__all__ = [
    "Config",
    "Finding",
    "Session",
    "Severity",
    "analyze",
    "instrument",
    "load_config",
    "session",
    "uninstrument",
    "watch",
]

__version__ = "0.1.0"
