from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization)\s*[:=]\s*[^\s]+"),
    re.compile(r"\b(?:sk|xoxb|xoxp|ghp|github_pat|hf|ya29|AIza)[A-Za-z0-9_\-\.]{8,}\b"),
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_\-]{20,}\b"),  # Telegram bot token shape
    re.compile(r"(?i)(refresh_token|access_token|id_token)\s*[:=]\s*[^\s,}\]]+"),
]
CHAT_ID_PATTERN = re.compile(r"(?<!\w)-?100\d{8,16}(?!\w)")


def redact(text: str, *, show_ids: bool = False) -> str:
    value = text
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    if not show_ids:
        value = CHAT_ID_PATTERN.sub("[REDACTED_ID]", value)
    return value


def redact_mapping_keys_only(mapping: dict[str, str]) -> dict[str, str]:
    return {key: "present" for key in sorted(mapping)}
