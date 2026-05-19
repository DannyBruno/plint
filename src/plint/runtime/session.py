"""Per-run tracing session: context manager + decorator."""

from __future__ import annotations

import contextvars
import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from plint.core.findings import Report
from plint.runtime.trace import Call, Trace

_CURRENT: contextvars.ContextVar["Session | None"] = contextvars.ContextVar(
    "plint_session", default=None
)


class Session:
    """A recording of all instrumented model calls within a scope, plus a report."""

    def __init__(self, name: str | None = None) -> None:
        self.name = name or "session"
        self.trace = Trace()
        self.started_at = time.time()
        self.ended_at: float | None = None
        self._report: Report | None = None

    def record(self, call: Call) -> None:
        self.trace.add(call)

    def report(self, *, use_judge: bool = False) -> Report:
        if self._report is not None:
            return self._report
        from plint.runtime.detectors import run_detectors

        rpt = Report()
        rpt.summary["session"] = self.name
        rpt.summary["call_count"] = len(self.trace.calls)
        rpt.summary["duration_s"] = round((self.ended_at or time.time()) - self.started_at, 3)
        rpt.extend(run_detectors(self.trace))
        if use_judge:
            try:
                from plint.runtime.confusion_judge import run_confusion_judge

                rpt.extend(run_confusion_judge(self.trace))
                rpt.summary["judge_ran"] = True
            except Exception as exc:
                rpt.summary["judge_ran"] = False
                rpt.summary["judge_error"] = str(exc)
        rpt.summary["finding_count"] = len(rpt.findings)
        self._report = rpt
        return rpt


def current_session() -> Session | None:
    return _CURRENT.get()


@contextmanager
def session(name: str | None = None, *, instrument_sdks: bool = True) -> Iterator[Session]:
    """Open a tracing session. Optionally instrument SDKs while open."""

    s = Session(name=name)
    token = _CURRENT.set(s)
    patched_here = False
    if instrument_sdks:
        from plint.runtime.instrument import instrument as do_instrument

        patched_here = do_instrument()
    try:
        yield s
    finally:
        s.ended_at = time.time()
        _CURRENT.reset(token)
        if patched_here and _CURRENT.get() is None:
            # Only uninstrument if no outer session is still active.
            from plint.runtime.instrument import uninstrument

            uninstrument()


def watch(
    _fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    report: str = "on_exit",
    use_judge: bool = False,
    on_report: Callable[[Report], None] | None = None,
) -> Callable[..., Any]:
    """Decorator equivalent of `session()` around a function.

    @plint.watch
    def run(): ...

    @plint.watch(name="onboarding", report="on_exit", use_judge=True)
    def run(): ...

    `report` may be:
      - "on_exit": print a text report when the function returns
      - "return": attach the Report as `.plint_report` on the wrapped function's return value (best-effort)
      - "callback": invoke `on_report` with the Report
      - "none": don't surface anything; the session is still discoverable via `current_session()`.
    """

    def _decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            with session(name=name or fn.__name__) as s:
                result = fn(*args, **kwargs)
            rpt = s.report(use_judge=use_judge)
            if report == "on_exit":
                from rich.console import Console

                from plint.report.text import write_text

                console = Console()
                console.rule(f"[bold]plint runtime report — {s.name}")
                write_text(rpt, console=console)
            elif report == "callback" and on_report is not None:
                on_report(rpt)
            elif report == "return":
                try:
                    setattr(result, "plint_report", rpt)
                except Exception:
                    pass
            return result

        return _wrapped

    if _fn is not None and callable(_fn):
        return _decorate(_fn)
    return _decorate
