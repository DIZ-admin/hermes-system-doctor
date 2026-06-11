from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..models import CheckResult, Finding, Severity
from ..path_utils import safe_relpath
from .discovery import profile_dirs

DRIFT_LOG_PATTERNS = {
    "post_update.import_error": re.compile(r"(?i)(ImportError|ModuleNotFoundError|cannot import|No module named)"),
    "post_update.version_mismatch": re.compile(r"(?i)(version mismatch|schema mismatch|config compatibility|migration required|deprecated config)"),
    "post_update.stale_process_hint": re.compile(r"(?i)(stale process|pid file race|another gateway instance|old process)"),
    "post_update.update_error": re.compile(r"(?i)(update failed|git pull failed|migration failed|dependency conflict|pip check failed)"),
}
MAX_LOG_BYTES = 64 * 1024
UPDATE_CACHE_NAMES = (".update_check", "update_check.json", "last_update_check.json")


def _safe_read_text_tail(path: Path, limit: int = MAX_LOG_BYTES) -> str | None:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return None
    try:
        stat = path.stat()
        with path.open("rb") as handle:
            if stat.st_size > limit:
                handle.seek(max(0, stat.st_size - limit))
            data = handle.read(limit)
    except OSError:
        return None
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def _git_ref(path: Path, ref: str) -> str | None:
    direct = path / ".git" / ref
    if direct.exists() and direct.is_file() and not direct.is_symlink():
        try:
            text = direct.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            return None
        return text[:40] if re.fullmatch(r"[0-9a-fA-F]{40}", text[:40]) else None
    packed = path / ".git" / "packed-refs"
    packed_text = _safe_read_text_tail(packed, 512 * 1024)
    if not packed_text:
        return None
    for line in packed_text.splitlines():
        if line.startswith("#") or " " not in line:
            continue
        sha, packed_ref = line.split(" ", 1)
        if packed_ref.strip() == ref and re.fullmatch(r"[0-9a-fA-F]{40}", sha):
            return sha
    return None


def _head_ref_and_sha(source_root: Path) -> tuple[str | None, str | None]:
    head = source_root / ".git" / "HEAD"
    text = _safe_read_text_tail(head, 4096)
    if not text:
        return None, None
    first = text.strip().splitlines()[0]
    if first.startswith("ref: "):
        ref = first.removeprefix("ref: ").strip()
        return ref, _git_ref(source_root, ref)
    if re.fullmatch(r"[0-9a-fA-F]{40}", first):
        return "detached", first
    return None, None


def _source_candidates(profile_path: Path) -> list[Path]:
    return [profile_path / "hermes-agent", profile_path.parent.parent / "hermes-agent"]


def _scan_drift_logs(profile_name: str, profile_path: Path, hermes_home: Path) -> tuple[dict[str, int], list[Finding], int]:
    counts = {key: 0 for key in DRIFT_LOG_PATTERNS}
    findings: list[Finding] = []
    scanned = 0
    logs_dir = profile_path / "logs"
    if logs_dir.is_symlink() or not logs_dir.is_dir():
        return counts, findings, scanned
    try:
        candidates = sorted(
            [p for p in logs_dir.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.lower() not in {".db", ".sqlite", ".gz", ".zip"}],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]
    except OSError:
        return counts, findings, scanned
    first_evidence: dict[str, list[str]] = {}
    for path in candidates:
        text = _safe_read_text_tail(path)
        if text is None:
            continue
        scanned += 1
        for line_no, line in enumerate(text.splitlines(), 1):
            for finding_id, regex in DRIFT_LOG_PATTERNS.items():
                if regex.search(line):
                    counts[finding_id] += 1
                    first_evidence.setdefault(finding_id, [safe_relpath(path, hermes_home), f"line={line_no}"])
    for finding_id, count in sorted(counts.items()):
        if count == 0:
            continue
        findings.append(
            Finding(
                id=finding_id,
                severity="WARN",
                component="post_update",
                profile=profile_name,
                summary=f"Post-update drift log signal matched {count} time(s)",
                evidence=[*first_evidence.get(finding_id, []), f"count={count}"],
                risk="Recent logs contain update/import/version/process drift signals. Raw log text is not included by default.",
                next_action="Inspect the local log around the reported line and run targeted Hermes status/doctor commands before restarting services.",
            )
        )
    return counts, findings, scanned


def _severity(findings: list[Finding]) -> Severity:
    if any(f.severity == "FAIL" for f in findings):
        return "FAIL"
    if any(f.severity == "UNKNOWN" for f in findings):
        return "UNKNOWN"
    if any(f.severity == "WARN" for f in findings):
        return "WARN"
    return "OK"


def post_update_drift_check(hermes_home: Path) -> CheckResult:
    findings: list[Finding] = []
    facts: dict[str, Any] = {
        "profiles_scanned": 0,
        "logs_scanned": 0,
        "signals": {},
        "source_candidates": [],
        "git_network_fetch": "not_run",
        "service_restarts": "not_run",
        "dependency_imports": "not_run",
    }
    source_seen: set[str] = set()
    for profile_name, profile_path in profile_dirs(hermes_home):
        facts["profiles_scanned"] += 1
        counts, log_findings, scanned = _scan_drift_logs(profile_name, profile_path, hermes_home)
        facts["logs_scanned"] += scanned
        facts["signals"].update({f"{profile_name}:{key}": value for key, value in counts.items()})
        findings.extend(log_findings)
        for cache_name in UPDATE_CACHE_NAMES:
            cache_path = profile_path / cache_name
            if cache_path.exists() and not cache_path.is_symlink():
                try:
                    age_seconds = max(0, int(__import__("time").time() - cache_path.stat().st_mtime))
                except OSError:
                    continue
                facts.setdefault("update_cache_files", {})[f"{profile_name}:{cache_name}"] = {"age_seconds": age_seconds}
                if age_seconds > 7 * 24 * 3600:
                    findings.append(
                        Finding(
                            id="post_update.cache_stale",
                            severity="UNKNOWN",
                            component="post_update",
                            profile=profile_name,
                            summary="Update-check cache is older than seven days",
                            evidence=[safe_relpath(cache_path, hermes_home), f"age_seconds={age_seconds}"],
                            risk="Local update status may be stale; the doctor did not fetch network state.",
                            next_action="Run the official Hermes update/status command manually if you need fresh upstream state.",
                        )
                    )
        for source_root in _source_candidates(profile_path):
            try:
                key = str(source_root.resolve())
            except OSError:
                key = str(source_root)
            if key in source_seen or not (source_root / ".git").exists():
                continue
            source_seen.add(key)
            label = safe_relpath(source_root, hermes_home)
            head_ref, head_sha = _head_ref_and_sha(source_root)
            origin_sha = _git_ref(source_root, "refs/remotes/origin/main")
            facts["source_candidates"].append(
                {"path": label, "head_ref": head_ref, "has_head_sha": bool(head_sha), "has_origin_main_ref": bool(origin_sha)}
            )
            if head_sha and origin_sha and head_sha != origin_sha:
                findings.append(
                    Finding(
                        id="post_update.local_origin_ref_differs",
                        severity="UNKNOWN",
                        component="post_update",
                        summary="Local Hermes checkout HEAD differs from local origin/main ref",
                        evidence=[label, f"head_ref={head_ref or 'unknown'}"],
                        risk="The checkout may be ahead, behind, or locally modified. No network fetch was run, so freshness is unknown.",
                        next_action="Run git status/fetch in the Hermes source checkout if you need exact update state.",
                    )
                )
            elif (source_root / ".git").exists() and not head_sha:
                findings.append(
                    Finding(
                        id="post_update.git_head_unknown",
                        severity="UNKNOWN",
                        component="post_update",
                        summary="Hermes source checkout exists but HEAD could not be resolved safely",
                        evidence=[label],
                        risk="The doctor cannot prove source version state from local metadata.",
                        next_action="Inspect the source checkout manually with git status before applying updates.",
                    )
                )
    severity = _severity(findings)
    summary = f"profiles={facts['profiles_scanned']} logs={facts['logs_scanned']} findings={len(findings)}"
    return CheckResult("post_update_drift", severity, summary, findings, facts)
