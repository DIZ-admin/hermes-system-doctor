from __future__ import annotations

import json

from .models import DoctorReport
from .redaction import redact


def to_json(report: DoctorReport) -> str:
    return redact(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


def to_markdown(report: DoctorReport) -> str:
    lines = [
        "# Hermes Agent System Doctor Report",
        "",
        f"Mode: `{report.mode}`",
        f"Status: `{report.status}`",
        f"Hermes home: `{redact(report.hermes_home)}`",
        f"Generated at: `{report.generated_at}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines += [
            "",
            f"### {check.name}",
            f"Severity: `{check.severity}`",
            f"Summary: {redact(check.summary)}",
        ]
        for finding in check.findings:
            lines += [
                "",
                f"- `{finding.severity}` `{finding.id}`: {redact(finding.summary)}",
            ]
            if finding.profile:
                lines.append(f"  - Profile: `{redact(finding.profile)}`")
            if finding.risk:
                lines.append(f"  - Risk: {redact(finding.risk)}")
            if finding.next_action:
                lines.append(f"  - Next action: `{redact(finding.next_action)}`")
            if finding.requires_approval:
                lines.append("  - Approval: required")
    return "\n".join(lines) + "\n"
