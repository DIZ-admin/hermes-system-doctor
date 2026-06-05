from __future__ import annotations

import re

TOKEN_SHAPE = (
    r"\b(?:"
    r"sk-[A-Za-z0-9_\-\.]{8,}|"
    r"xox[baprs]-[A-Za-z0-9\-]{8,}|"
    r"ghp_[A-Za-z0-9_]{8,}|"
    r"github_pat_[A-Za-z0-9_]+|"
    r"hf_[A-Za-z0-9_\-]{8,}|"
    r"ya29\.[A-Za-z0-9_\-\.]{8,}|"
    r"AIza[A-Za-z0-9_\-]{8,}"
    r")\b"
)

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization)\s*[:=]\s*[^\s]+"),
    re.compile(TOKEN_SHAPE),
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
