from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..models import CheckResult, Finding, Severity
from ..path_utils import safe_relpath
from .discovery import profile_dirs

MAX_LOG_FILES_PER_PROFILE = 5
MAX_BYTES_PER_FILE = 64 * 1024
MAX_TOTAL_BYTES = 512 * 1024
SKIP_SUFFIXES = {".gz", ".zip", ".sqlite", ".db", ".bin"}

CATEGORY_PATTERNS = {
    "log.auth_error": re.compile(r"(?i)(auth failed|unauthorized|invalid api key|oauth|\b401\b|\b403\b)"),
    "log.gateway_shutdown": re.compile(r"(?i)(gateway shutdown|stopping gateway|received sigterm|disconnect|reconnect failed)"),
    "log.duplicate_process": re.compile(r"(?i)(address already in use|port already in use|duplicate|already running)"),
    "log.provider_error": re.compile(r"(?i)(provider error|rate limit|\b429\b|model[ ._-]?not[ ._-]?found|api error)"),
    "log.mcp_error": re.compile(r"(?i)(mcp[ ._-]?error|mcp[ ._-]?failed)"),
    "log.cron_error": re.compile(r"(?i)(cron[ ._-]?error|job[ ._-]?failed|scheduler[ ._-]?error)"),
    "log.import_error": re.compile(r"(?i)(ImportError|ModuleNotFoundError|cannot import)"),
    "log.compression_error": re.compile(r"(?i)(compression[ ._-]?failed|context compression|compression summary failed)"),
}


def _regular_log_files(logs_dir: Path) -> tuple[list[Path], int]:
    if not logs_dir.is_dir() or logs_dir.is_symlink():
        return [], 0
    files: list[Path] = []
    skipped = 0
    for path in logs_dir.iterdir():
        if path.is_symlink():
            skipped += 1
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            skipped += 1
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_LOG_FILES_PER_PROFILE], skipped


def logs_check(hermes_home: Path) -> CheckResult:
    facts: dict[str, Any] = {
        "profiles_with_logs": 0,
        "files_scanned": 0,
        "bytes_scanned": 0,
        "categories": {},
        "skipped_files": 0,
    }
    findings: list[Finding] = []
    category_counts: Counter[str] = Counter()
    category_evidence: dict[str, list[str]] = {}
    total_bytes = 0

    for profile_name, profile_path in profile_dirs(hermes_home):
        logs_dir = profile_path / "logs"
        if logs_dir.is_symlink():
            facts["skipped_files"] += 1
            continue
        if not logs_dir.exists():
            continue
        facts["profiles_with_logs"] += 1
        log_files, skipped = _regular_log_files(logs_dir)
        facts["skipped_files"] += skipped
        for path in log_files:
            remaining = MAX_TOTAL_BYTES - total_bytes
            if remaining <= 0:
                facts["skipped_files"] += 1
                continue
            try:
                with path.open("rb") as handle:
                    data = handle.read(min(MAX_BYTES_PER_FILE, remaining))
            except OSError:
                facts["skipped_files"] += 1
                continue
            total_bytes += len(data)
            facts["bytes_scanned"] = total_bytes
            if b"\0" in data:
                facts["skipped_files"] += 1
                continue
            facts["files_scanned"] += 1
            text = data.decode("utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), 1):
                for category, regex in CATEGORY_PATTERNS.items():
                    if regex.search(line):
                        category_counts[category] += 1
                        category_evidence.setdefault(category, [
                            safe_relpath(path, hermes_home),
                            f"line={line_no}",
                        ])

    facts["categories"] = dict(sorted(category_counts.items()))
    for category, count in sorted(category_counts.items()):
        findings.append(
            Finding(
                id=category,
                severity="WARN",
                component="logs",
                summary=f"Log category matched {count} time(s)",
                evidence=[*category_evidence.get(category, []), f"count={count}"],
                risk="Recent logs contain a known failure signal. The report does not include raw log text by default.",
                next_action="Inspect the local log file directly before restarting or changing configuration.",
            )
        )

    if category_counts:
        severity: Severity = "WARN"
    elif facts["profiles_with_logs"] == 0:
        severity = "OK"
    else:
        severity = "OK"
    return CheckResult("logs", severity, f"files={facts['files_scanned']} categories={len(category_counts)}", findings, facts)
