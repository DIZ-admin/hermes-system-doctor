from __future__ import annotations

from pathlib import Path

from ..models import CheckResult, Finding
from ..path_utils import safe_relpath


def profile_dirs(hermes_home: Path) -> list[tuple[str, Path]]:
    profiles: list[tuple[str, Path]] = []
    if (hermes_home / "config.yaml").exists():
        profiles.append(("default", hermes_home))
    profiles_root = hermes_home / "profiles"
    if profiles_root.is_dir() and not profiles_root.is_symlink():
        profiles.extend((p.name, p) for p in sorted(profiles_root.iterdir()) if p.is_dir() and not p.is_symlink())
    return profiles


def discover_home(hermes_home: Path) -> CheckResult:
    facts = {"exists": hermes_home.exists(), "profiles": []}
    findings: list[Finding] = []
    if not hermes_home.exists():
        findings.append(
            Finding(
                id="home.missing",
                severity="FAIL",
                component="home",
                summary="Hermes home does not exist",
                evidence=["[REDACTED_PATH]"],
                risk="The doctor cannot inventory a missing Hermes home.",
                next_action="Pass --hermes-home PATH or install/configure Hermes Agent first.",
            )
        )
        return CheckResult("discovery", "FAIL", "Hermes home missing", findings, facts)

    profiles_root = hermes_home / "profiles"
    if profiles_root.exists() and not profiles_root.is_dir():
        findings.append(
            Finding(
                id="profiles.path_not_directory",
                severity="FAIL",
                component="profiles",
                summary="profiles path exists but is not a directory",
                evidence=[safe_relpath(profiles_root, hermes_home)],
                risk="Named profiles cannot be discovered from this Hermes home.",
                next_action="Move or remove the blocking profiles file, then restore the profiles directory if needed.",
            )
        )

    profiles = [name for name, _ in profile_dirs(hermes_home)]
    facts["profiles"] = profiles
    facts["profiles_count"] = len(profiles)
    facts["inspected_default_home"] = str(hermes_home.expanduser()) == str(Path("~/.hermes").expanduser())
    severity = "FAIL" if any(f.severity == "FAIL" for f in findings) else "OK" if profiles else "UNKNOWN"
    summary = f"profiles={len(profiles)}"
    if not profiles:
        findings.append(
            Finding(
                id="profiles.none_detected",
                severity="UNKNOWN",
                component="profiles",
                summary="No Hermes profiles detected",
                risk="This may be an empty or non-standard Hermes home.",
                next_action="Run hermes profile list or pass --hermes-home explicitly.",
            )
        )
    return CheckResult("discovery", severity, summary, findings, facts)
