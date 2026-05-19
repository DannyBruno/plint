"""JSON output for CI consumption."""

from __future__ import annotations

import json
import sys
from typing import TextIO

from plint.core.findings import Report


def write_json(report: Report, stream: TextIO | None = None) -> None:
    stream = stream or sys.stdout
    json.dump(report.to_dict(), stream, indent=2, default=str)
    stream.write("\n")
