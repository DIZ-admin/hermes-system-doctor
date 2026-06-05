from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .redaction import redact

SAFE_ACTION_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")


@dataclass
class BackupPreview:
    required: bool
    performed: bool
    reason: str
    files: list[str] = field(default_factory=list)


@dataclass
class DiffPreview:
    available: bool
    reason: str
    entries: list[str] = field(default_factory=list)


@dataclass
class FixPreview:
    schema_version: str
    generated_at: str
    dry_run: bool
    execute_requested: bool
    status: str
    approved_action_id: str
    side_effects_performed: list[str]
    action: dict[str, Any] | None
    backup: BackupPreview
    diff: DiffPreview
    rollback_hint: str | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_repair_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("repair plan JSON must be an object")
    return data


def _safe_action_id(action_id: str) -> str:
    candidate = str(action_id or "").strip()
    if not SAFE_ACTION_ID.fullmatch(candidate):
        raise ValueError("approved action id must contain only letters, numbers, dot, colon, underscore, or dash")
    return candidate


def _actions(plan: dict[str, Any]) -> list[dict[str, Any]]:
    raw = plan.get("actions", [])
    if not isinstance(raw, list):
        raise ValueError("repair plan actions must be a list")
    actions: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            actions.append(item)
    return actions


def _find_action(plan: dict[str, Any], action_id: str) -> dict[str, Any] | None:
    matches = [action for action in _actions(plan) if action.get("action_id") == action_id]
    if len(matches) > 1:
        raise ValueError("repair plan contains duplicate action ids")
    return matches[0] if matches else None


def build_fix_preview(plan: dict[str, Any], approve_action_id: str, *, execute: bool = False) -> FixPreview:
    action_id = _safe_action_id(approve_action_id)
    if plan.get("dry_run_only") is not True:
        raise ValueError("input must be a dry-run repair plan produced by repair-plan mode")

    action = _find_action(plan, action_id)
    notes = [
        "This is the gated fix executor skeleton. It validates one approved action id and renders backup/diff/rollback intent.",
        "No repair executors are registered yet, so this command does not edit files, restart services, run cron jobs, execute plugins, execute MCP tools, or perform network calls.",
    ]
    if action is None:
        return FixPreview(
            schema_version="1.0",
            generated_at=datetime.now(timezone.utc).isoformat(),
            dry_run=not execute,
            execute_requested=execute,
            status="BLOCKED_ACTION_NOT_FOUND",
            approved_action_id=action_id,
            side_effects_performed=[],
            action=None,
            backup=BackupPreview(required=False, performed=False, reason="No matching action was found."),
            diff=DiffPreview(available=False, reason="No matching action was found."),
            rollback_hint=None,
            notes=notes,
        )

    approval_required = action.get("approval_required") is True
    mode = str(action.get("mode") or "unknown")
    backup_required = action.get("backup_required") is True
    rollback_hint = _rollback_hint(action)

    if not approval_required:
        status = "BLOCKED_UNTRUSTED_PLAN_ACTION"
        backup_reason = "Plan action did not require approval; refusing to treat it as safe input."
        diff_reason = backup_reason
    elif mode == "manual_diagnostic":
        status = "BLOCKED_DIAGNOSTIC_ONLY"
        backup_reason = "Diagnostic-only action; no backup should be made because no mutation is allowed."
        diff_reason = "Diagnostic-only action; inspect manually and re-run the doctor instead of applying a fix."
    elif execute:
        status = "BLOCKED_NO_EXECUTOR"
        backup_reason = "Execution was requested, but no safe executor is registered for this action yet. Backup not created because no write will occur."
        diff_reason = "No file diff is available because this preview has no registered mutation for the action."
    else:
        status = "DRY_RUN_READY"
        backup_reason = "Backup would be required before any future mutation. Not performed in dry-run preview."
        diff_reason = "No file diff is available because this skeleton does not include repair executors yet."

    return FixPreview(
        schema_version="1.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        dry_run=not execute,
        execute_requested=execute,
        status=status,
        approved_action_id=action_id,
        side_effects_performed=[],
        action=_safe_action_summary(action),
        backup=BackupPreview(required=backup_required, performed=False, reason=backup_reason),
        diff=DiffPreview(available=False, reason=diff_reason),
        rollback_hint=rollback_hint,
        notes=notes,
    )


def _rollback_hint(action: dict[str, Any]) -> str:
    mode = str(action.get("mode") or "unknown")
    if mode == "manual_diagnostic":
        return "No rollback is needed for diagnostic-only actions because no mutation is allowed."
    return "Restore the pre-change backup for any edited file and re-run hermes-system-doctor before restarting services."


def _safe_action_summary(action: dict[str, Any]) -> dict[str, Any]:
    safe_action_id = (
        _safe_action_id(str(action.get("action_id") or "unknown"))
        if SAFE_ACTION_ID.fullmatch(str(action.get("action_id") or ""))
        else "unknown"
    )
    components = {
        "auth_surface",
        "config",
        "cron",
        "gateway",
        "logs",
        "mcp",
        "memory",
        "plugins",
        "post_update",
        "post_update_drift",
        "profiles",
        "skills",
        "discovery",
    }
    severities = {"OK", "WARN", "FAIL", "UNKNOWN", "NEEDS_APPROVAL"}
    modes = {"manual_diagnostic", "approval_gated_repair_candidate"}
    files = action.get("files_that_would_change")
    return {
        "action_id": safe_action_id,
        "component": _safe_enum(action.get("component"), components, "unknown"),
        "severity": _safe_enum(action.get("severity"), severities, "UNKNOWN"),
        "mode": _safe_enum(action.get("mode"), modes, "unknown"),
        "profile_present": isinstance(action.get("profile"), str) and bool(action.get("profile")),
        "approval_required": action.get("approval_required") is True,
        "backup_required": action.get("backup_required") is True,
        "destructive": action.get("destructive") is True,
        "files_that_would_change_count": len(files) if isinstance(files, list) else 0,
    }


def _safe_enum(value: Any, allowed: set[str], fallback: str) -> str:
    candidate = str(value or "").strip()
    return candidate if candidate in allowed else fallback


def fix_preview_to_json(preview: FixPreview) -> str:
    return redact(json.dumps(preview.to_dict(), ensure_ascii=False, indent=2)) + "\n"


def fix_preview_to_markdown(preview: FixPreview) -> str:
    lines = [
        "# Hermes Agent System Doctor Fix Preview",
        "",
        f"Schema: `{preview.schema_version}`",
        f"Approved action: `{redact(preview.approved_action_id)}`",
        f"Status: `{redact(preview.status)}`",
        f"Dry run: `{str(preview.dry_run).lower()}`",
        f"Execute requested: `{str(preview.execute_requested).lower()}`",
        "",
        "## Safety",
    ]
    for note in preview.notes:
        lines.append(f"- {redact(note)}")
    lines += [
        f"- Side effects performed: `{len(preview.side_effects_performed)}`",
        f"- Backup required: `{str(preview.backup.required).lower()}`",
        f"- Backup performed: `{str(preview.backup.performed).lower()}`",
        f"- Backup note: {redact(preview.backup.reason)}",
        f"- Diff available: `{str(preview.diff.available).lower()}`",
        f"- Diff note: {redact(preview.diff.reason)}",
    ]
    if preview.rollback_hint:
        lines.append(f"- Rollback hint: {redact(preview.rollback_hint)}")
    if preview.action:
        lines += ["", "## Action"]
        for key in ("action_id", "finding_id", "component", "severity", "mode"):
            if key in preview.action:
                lines.append(f"- {key}: `{redact(str(preview.action[key]))}`")
    return "\n".join(lines) + "\n"
