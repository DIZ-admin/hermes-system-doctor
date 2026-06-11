from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import CheckResult, Finding, Severity
from .discovery import profile_dirs


def profile_inventory_check(hermes_home: Path) -> CheckResult:
    findings: list[Finding] = []
    profiles = profile_dirs(hermes_home)
    facts: dict[str, Any] = {"profiles": []}
    for name, path in profiles:
        facts["profiles"].append(
            {
                "name": name,
                "has_config": (path / "config.yaml").exists(),
                "has_logs_dir": (path / "logs").is_dir(),
                "has_skills_dir": (path / "skills").is_dir(),
                "has_cron_dir": (path / "cron").is_dir(),
                "has_plugins_dir": (path / "plugins").is_dir(),
            }
        )
    if not profiles and hermes_home.exists():
        findings.append(
            Finding(
                id="profiles.empty_home",
                severity="UNKNOWN",
                component="profiles",
                summary="Hermes home exists but no root or named profiles were detected",
                risk="The installation may be empty, non-standard, or not initialized yet.",
                next_action="Run hermes setup or pass the correct --hermes-home path.",
            )
        )
    severity: Severity = "UNKNOWN" if findings else "OK"
    return CheckResult("profiles", severity, f"profiles={len(profiles)}", findings, facts)
