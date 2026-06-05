from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from ..models import CheckResult, Finding
from ..path_utils import safe_relpath
from .discovery import profile_dirs

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "sessions", "__" + "pycache__"}
UNEXPECTED_DIRS = {"logs", "sessions", "reports", "tmp", "cache", "caches", "workdir", "workspace"}
MAX_DEPTH = 3


def _category(name: str) -> str | None:
    lower = name.lower()
    if lower == ".env" or lower.startswith(".env."):
        return "auth_surface.env_file"
    if lower in {"auth.json", "oauth.json", "token.json", "tokens.json", "credentials.json"}:
        return "auth_surface.auth_store"
    if "credential" in lower or lower.startswith("auth_pool"):
        return "auth_surface.credential_pool"
    if lower.startswith("cookie") or lower in {"cookies.sqlite", "browser_state.json", "storage_state.json"}:
        return "auth_surface.cookie_store_like"
    if lower in {"id_rsa", "id_ed25519"} or lower.endswith((".pem", ".key", ".p12")):
        return "auth_surface.private_key_like"
    return None


def _walk_shallow(root: Path):
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_DEPTH or not current.is_dir() or current.is_symlink():
            continue
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            yield child, depth + 1
            if child.is_dir() and not child.is_symlink() and child.name not in SKIP_DIRS:
                stack.append((child, depth + 1))


def _unexpected(path: Path, profile_path: Path) -> bool:
    try:
        rel = path.relative_to(profile_path)
    except ValueError:
        return True
    parts = rel.parts[:-1]
    return any(part.lower() in UNEXPECTED_DIRS for part in parts)


def _scan_roots(hermes_home: Path) -> list[tuple[str, Path]]:
    roots = profile_dirs(hermes_home)
    if hermes_home.exists() and all(path != hermes_home for _name, path in roots):
        roots.insert(0, ("home", hermes_home))
    return roots


def auth_surface_check(hermes_home: Path) -> CheckResult:
    findings: list[Finding] = []
    counts: Counter[str] = Counter()
    profiles: dict[str, dict[str, int]] = defaultdict(dict)
    scanned_profiles = 0
    skipped_symlinks = 0

    for profile_name, profile_path in _scan_roots(hermes_home):
        scanned_profiles += 1
        for path, _depth in _walk_shallow(profile_path):
            if path.is_symlink():
                skipped_symlinks += 1
                findings.append(
                    Finding(
                        id="auth_surface.symlink_skipped",
                        severity="WARN",
                        component="auth_surface",
                        profile=profile_name,
                        summary="Auth-surface scan skipped a symlink",
                        evidence=[safe_relpath(path, hermes_home)],
                        risk="Symlink targets are not inspected to avoid reading outside the selected Hermes home.",
                        next_action="Inspect the symlink manually if it is expected.",
                    )
                )
                continue
            category = _category(path.name)
            if not category:
                continue
            counts[category] += 1
            profiles[profile_name][category] = profiles[profile_name].get(category, 0) + 1
            finding_id = "auth_surface.unexpected_location" if _unexpected(path, profile_path) else category
            severity = "WARN"
            findings.append(
                Finding(
                    id=finding_id,
                    severity=severity,
                    component="auth_surface",
                    profile=profile_name,
                    summary="Auth/secret-adjacent file name detected",
                    evidence=[category, safe_relpath(path, hermes_home)],
                    risk="The doctor reports presence only and does not read credential payloads.",
                    next_action="Verify locally that this file belongs in this profile and is not committed or shared.",
                )
            )

    facts = {
        "profiles_scanned": scanned_profiles,
        "categories": dict(sorted(counts.items())),
        "profiles": {profile: dict(sorted(values.items())) for profile, values in sorted(profiles.items())},
        "skipped_symlinks": skipped_symlinks,
    }
    severity = "WARN" if findings else "OK" if scanned_profiles else "UNKNOWN"
    if scanned_profiles == 0:
        findings.append(
            Finding(
                id="auth_surface.no_profiles",
                severity="UNKNOWN",
                component="auth_surface",
                summary="No profiles were available for auth-surface inventory",
                risk="Credential-adjacent surfaces cannot be inventoried without profiles.",
                next_action="Run discovery or pass the correct --hermes-home path.",
            )
        )
    return CheckResult("auth_surface", severity, f"categories={len(counts)} findings={len(findings)}", findings, facts)
