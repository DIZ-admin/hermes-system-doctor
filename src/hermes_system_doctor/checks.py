from __future__ import annotations

from pathlib import Path
from .models import CheckResult, Finding


def discover_home(hermes_home: Path) -> CheckResult:
    facts = {"exists": hermes_home.exists(), "profiles": []}
    findings: list[Finding] = []
    if not hermes_home.exists():
        findings.append(Finding(
            id="home.missing",
            severity="FAIL",
            component="home",
            summary="Hermes home does not exist",
            evidence=[str(hermes_home)],
            risk="The doctor cannot inventory a missing Hermes home.",
            next_action="Pass --hermes-home PATH or install/configure Hermes Agent first.",
        ))
        return CheckResult("discovery", "FAIL", "Hermes home missing", findings, facts)

    profiles_root = hermes_home / "profiles"
    profiles = []
    if (hermes_home / "config.yaml").exists():
        profiles.append("default")
    if profiles_root.exists():
        profiles.extend(sorted(p.name for p in profiles_root.iterdir() if p.is_dir()))
    facts["profiles"] = profiles
    severity = "OK" if profiles else "UNKNOWN"
    summary = f"profiles={len(profiles)}"
    if not profiles:
        findings.append(Finding(
            id="profiles.none_detected",
            severity="UNKNOWN",
            component="profiles",
            summary="No Hermes profiles detected",
            risk="This may be an empty or non-standard Hermes home.",
            next_action="Run hermes profile list or pass --hermes-home explicitly.",
        ))
    return CheckResult("discovery", severity, summary, findings, facts)


def profile_config_check(hermes_home: Path) -> CheckResult:
    findings: list[Finding] = []
    profile_dirs: list[tuple[str, Path]] = []
    if (hermes_home / "config.yaml").exists():
        profile_dirs.append(("default", hermes_home))
    profiles_root = hermes_home / "profiles"
    if profiles_root.exists():
        profile_dirs.extend((p.name, p) for p in sorted(profiles_root.iterdir()) if p.is_dir())

    for name, path in profile_dirs:
        if not (path / "config.yaml").exists():
            findings.append(Finding(
                id="profile.config_missing",
                severity="WARN",
                component="profiles",
                profile=name,
                summary="Profile directory has no config.yaml",
                evidence=[str(path.name)],
                risk="The profile may be incomplete or stale.",
                next_action=f"Run hermes --profile {name} config path, or recreate/export the profile if needed.",
            ))
    severity = "WARN" if findings else "OK"
    return CheckResult("profiles", severity, f"checked={len(profile_dirs)} findings={len(findings)}", findings, {"checked": len(profile_dirs)})
