"""Registry of runtime detectors."""

from plint.core.findings import Finding
from plint.runtime.trace import Trace


def run_detectors(trace: Trace) -> list[Finding]:
    """Run all detectors over a completed trace, returning findings."""

    from plint.runtime.detectors.tool_loop import detect_tool_loop
    from plint.runtime.detectors.tool_orphan import detect_tool_orphan
    from plint.runtime.detectors.tool_oscillation import detect_tool_oscillation
    from plint.runtime.detectors.tool_arg_drift import detect_tool_arg_drift
    from plint.runtime.detectors.hedging import detect_hedging
    from plint.runtime.detectors.skill_unused import detect_skill_unused

    out: list[Finding] = []
    out.extend(detect_tool_loop(trace))
    out.extend(detect_tool_oscillation(trace))
    out.extend(detect_tool_orphan(trace))
    out.extend(detect_tool_arg_drift(trace))
    out.extend(detect_hedging(trace))
    out.extend(detect_skill_unused(trace))
    return out
