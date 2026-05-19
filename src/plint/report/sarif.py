"""SARIF 2.1.0 output — surfaces findings in the GitHub code-scanning UI."""

from __future__ import annotations

import json
import sys
from typing import TextIO

from plint.core.findings import Report, Severity

_SEV_TO_SARIF = {
    Severity.ERROR: "error",
    Severity.WARN: "warning",
    Severity.INFO: "note",
}


def write_sarif(report: Report, stream: TextIO | None = None) -> None:
    stream = stream or sys.stdout

    rules: dict[str, dict] = {}
    results: list[dict] = []
    for f in report.findings:
        rules.setdefault(
            f.rule_id,
            {
                "id": f.rule_id,
                "name": f.rule_id,
                "shortDescription": {"text": f.rule_id},
                "fullDescription": {"text": f.message},
                "defaultConfiguration": {"level": _SEV_TO_SARIF[f.severity]},
            },
        )
        result: dict = {
            "ruleId": f.rule_id,
            "level": _SEV_TO_SARIF[f.severity],
            "message": {"text": f.message + (f"\n→ {f.suggestion}" if f.suggestion else "")},
        }
        if f.path:
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": str(f.path)},
                        "region": {"startLine": f.line or 1},
                    }
                }
            ]
        results.append(result)

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "plint",
                        "informationUri": "https://github.com/your-org/plint",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    json.dump(sarif, stream, indent=2)
    stream.write("\n")
