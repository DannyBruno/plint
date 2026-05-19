"""Demonstrate the runtime API without needing live model access.

Builds a synthetic Trace that exhibits a tool-loop, an orphaned tool call, and hedging,
then runs the detectors and prints the report.
"""

from __future__ import annotations

import plint
from plint.report.text import write_text
from plint.runtime.session import Session
from plint.runtime.trace import Call, ToolInvocation


def main() -> None:
    s = Session(name="synthetic-demo")

    # Three identical tool calls in a row → loop
    for _ in range(3):
        s.record(
            Call(
                provider="anthropic",
                model="claude-sonnet-4-6",
                system="You are an assistant. Use the search_docs tool to find information.",
                assistant_text="I'll search for that.",
                tool_calls=[ToolInvocation(name="search_docs", arguments={"q": "policy"}, raw={"id": "t1"})],
            )
        )

    # Hedging response
    s.record(
        Call(
            provider="anthropic",
            model="claude-sonnet-4-6",
            assistant_text=(
                "I'm not sure what you mean. Could you clarify what you're looking for? "
                "Without more context, I'll assume you wanted the safety policy."
            ),
            tool_calls=[],
        )
    )

    # Orphaned tool call (no result follow-up)
    s.record(
        Call(
            provider="anthropic",
            model="claude-sonnet-4-6",
            assistant_text="",
            tool_calls=[ToolInvocation(name="fetch_record", arguments={"id": "42"}, raw={"id": "t99"})],
        )
    )
    # Next call has no tool_result for t99
    s.record(
        Call(
            provider="anthropic",
            model="claude-sonnet-4-6",
            assistant_text="Anyway, here's a different answer entirely.",
            messages=[{"role": "user", "content": "What about the other thing?"}],
        )
    )

    print(f"plint version: {plint.__version__}")
    report = s.report(use_judge=False)
    write_text(report)


if __name__ == "__main__":
    main()
