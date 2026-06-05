import json
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_system_doctor.fix_executor import build_fix_preview

TRAPS = [
    "LEAK_TRAP_FIX_SECRET",
    "LEAK_TRAP_FIX_RAW_LOG",
]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "hermes_system_doctor.cli", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def assert_no_traps(output: str):
    for trap in TRAPS:
        assert trap not in output


def sample_plan():
    return {
        "schema_version": "1.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_report_mode": "full",
        "source_report_status": "WARN",
        "dry_run_only": True,
        "notes": ["LEAK_TRAP_FIX_SECRET should not matter if not copied from action evidence"],
        "actions": [
            {
                "action_id": "rp-0001",
                "finding_id": "config.missing",
                "component": "config",
                "severity": "WARN",
                "profile": "default",
                "title": "config.missing",
                "mode": "approval_gated_repair_candidate",
                "approval_required": True,
                "backup_required": True,
                "destructive": False,
                "files_that_would_change": ["config.yaml"],
                "manual_command": "hermes config path",
                "proposed_change": "Prepare a backup first. LEAK_TRAP_FIX_RAW_LOG",
                "rollback_hint": "Restore backup.",
                "risk": "Profile may be incomplete.",
                "source_evidence": ["evidence_items=1"],
            },
            {
                "action_id": "rp-0002",
                "finding_id": "gateway.sigterm_seen",
                "component": "gateway",
                "severity": "WARN",
                "profile": "default",
                "title": "gateway.sigterm_seen",
                "mode": "manual_diagnostic",
                "approval_required": True,
                "backup_required": False,
                "destructive": False,
                "files_that_would_change": [],
                "manual_command": "hermes gateway status",
                "proposed_change": "No automatic change is included.",
                "rollback_hint": "No rollback needed.",
                "risk": "Gateway lifecycle signal.",
                "source_evidence": ["evidence_items=2"],
            },
        ],
    }


def test_fix_preview_requires_plan_and_approval(tmp_path):
    missing_plan = run_cli("fix", "--approve", "rp-0001")
    assert missing_plan.returncode != 0
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")
    missing_approval = run_cli("fix", "--plan", str(plan_path))
    assert missing_approval.returncode != 0


def test_fix_preview_dry_run_validates_action_without_writes(tmp_path):
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "fix-preview.json"
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    marker = hermes_home / "marker.txt"
    marker.write_text("sentinel", encoding="utf-8")
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")

    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    result = run_cli(
        "fix",
        "--hermes-home",
        str(hermes_home),
        "--plan",
        str(plan_path),
        "--approve",
        "rp-0001",
        "--output",
        str(output_path),
    )
    assert result.returncode == 0, result.stderr
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert after == before | {output_path.relative_to(tmp_path)}
    assert marker.read_text(encoding="utf-8") == "sentinel"

    payload = output_path.read_text(encoding="utf-8")
    assert_no_traps(payload)
    data = json.loads(payload)
    assert data["status"] == "DRY_RUN_READY"
    assert data["dry_run"] is True
    assert data["execute_requested"] is False
    assert data["side_effects_performed"] == []
    assert data["backup"]["required"] is True
    assert data["backup"]["performed"] is False
    assert data["diff"]["available"] is True
    assert data["action"]["action_id"] == "rp-0001"
    assert data["action"]["registered_executor"] is True


def test_fix_execute_applies_config_missing_with_backup_manifest(tmp_path):
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "execute-preview.json"
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    marker = hermes_home / "marker.txt"
    marker.write_text("sentinel", encoding="utf-8")
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")

    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    result = run_cli(
        "fix",
        "--hermes-home",
        str(hermes_home),
        "--plan",
        str(plan_path),
        "--approve",
        "rp-0001",
        "--execute",
        "--output",
        str(output_path),
    )
    assert result.returncode == 0, result.stderr
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    created = after - before
    assert output_path.relative_to(tmp_path) in created
    assert (hermes_home / "config.yaml").relative_to(tmp_path) in created
    assert any(str(path).endswith("MANIFEST.json") for path in created)
    assert marker.read_text(encoding="utf-8") == "sentinel"
    assert "Created by hermes-system-doctor" in (hermes_home / "config.yaml").read_text(encoding="utf-8")
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["status"] == "APPLIED"
    assert data["execute_requested"] is True
    assert data["side_effects_performed"] == ["backup_manifest_written", "config_stub_written"]
    assert data["backup"]["performed"] is True
    assert data["diff"]["available"] is True


def test_fix_blocks_diagnostic_only_missing_existing_and_unregistered_actions(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan = sample_plan()
    plan["actions"].append(
        {
            "action_id": "rp-0003",
            "finding_id": "cron.script_missing",
            "component": "cron",
            "severity": "WARN",
            "profile": "default",
            "title": "cron.script_missing",
            "mode": "approval_gated_repair_candidate",
            "approval_required": True,
            "backup_required": True,
            "destructive": False,
            "files_that_would_change": [],
        }
    )
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    diagnostic = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0002")
    assert diagnostic.returncode == 1
    diagnostic_data = json.loads(diagnostic.stdout)
    assert diagnostic_data["status"] == "BLOCKED_DIAGNOSTIC_ONLY"
    assert diagnostic_data["backup"]["required"] is False

    missing = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-9999")
    assert missing.returncode == 1
    missing_data = json.loads(missing.stdout)
    assert missing_data["status"] == "BLOCKED_ACTION_NOT_FOUND"

    unregistered = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0003", "--execute")
    assert unregistered.returncode == 2
    unregistered_data = json.loads(unregistered.stdout)
    assert unregistered_data["status"] == "BLOCKED_NO_EXECUTOR"

    hermes_home = tmp_path / "hermes-existing"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text("{}\n", encoding="utf-8")
    existing = run_cli(
        "fix",
        "--hermes-home",
        str(hermes_home),
        "--plan",
        str(plan_path),
        "--approve",
        "rp-0001",
        "--execute",
    )
    assert existing.returncode == 2
    existing_data = json.loads(existing.stdout)
    assert existing_data["status"] == "BLOCKED_TARGET_EXISTS"


def test_fix_config_missing_from_real_report_resolves_doctor_finding(tmp_path):
    hermes_home = tmp_path / "hermes"
    profile_dir = hermes_home / "profiles" / "operator"
    profile_dir.mkdir(parents=True)
    report_path = tmp_path / "report.json"
    plan_path = tmp_path / "plan.json"
    preview_path = tmp_path / "preview.json"

    report = run_cli("full", "--hermes-home", str(hermes_home), "--json", "--output", str(report_path))
    assert report.returncode == 0, report.stderr
    first_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert any(
        finding["id"] == "config.missing"
        for check in first_report["checks"]
        for finding in check["findings"]
    )

    plan_result = run_cli("repair-plan", "--input", str(report_path), "--output", str(plan_path))
    assert plan_result.returncode == 0, plan_result.stderr
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    action_id = next(action["action_id"] for action in plan["actions"] if action["finding_id"] == "config.missing")

    applied = run_cli(
        "fix",
        "--hermes-home",
        str(hermes_home),
        "--plan",
        str(plan_path),
        "--approve",
        action_id,
        "--execute",
        "--output",
        str(preview_path),
    )
    assert applied.returncode == 0, applied.stderr
    assert (profile_dir / "config.yaml").exists()
    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    assert preview["status"] == "APPLIED"
    assert preview["backup"]["performed"] is True

    second_report = run_cli("full", "--hermes-home", str(hermes_home), "--json")
    assert second_report.returncode == 0, second_report.stderr
    second = json.loads(second_report.stdout)
    assert not any(
        finding["id"] == "config.missing"
        for check in second["checks"]
        for finding in check["findings"]
    )


def test_fix_rejects_untrusted_plan_and_malicious_action_id(tmp_path):
    plan = sample_plan()
    plan["dry_run_only"] = False
    bad_plan_path = tmp_path / "bad-plan.json"
    bad_plan_path.write_text(json.dumps(plan), encoding="utf-8")
    bad_plan = run_cli("fix", "--plan", str(bad_plan_path), "--approve", "rp-0001")
    assert bad_plan.returncode != 0
    assert "Traceback" not in bad_plan.stderr

    good_plan_path = tmp_path / "good-plan.json"
    good_plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")
    malicious = run_cli("fix", "--plan", str(good_plan_path), "--approve", "rp-0001;rm -rf ~/.hermes")
    assert malicious.returncode != 0
    assert "Traceback" not in malicious.stderr
    assert "rm -rf" not in malicious.stdout


def test_fix_preview_does_not_echo_untrusted_allowed_plan_fields(tmp_path):
    plan = sample_plan()
    plan["actions"][0].update(
        {
            "finding_id": "LEAK_TRAP_FIX_SECRET",
            "component": "LEAK_TRAP_FIX_SECRET",
            "severity": "LEAK_TRAP_FIX_SECRET",
            "profile": "LEAK_TRAP_FIX_RAW_LOG",
            "mode": "LEAK_TRAP_FIX_SECRET",
            "files_that_would_change": ["/tmp/LEAK_TRAP_FIX_RAW_LOG/config.yaml"],
        }
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    result = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0001")
    assert result.returncode != 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    assert data["action"]["component"] == "unknown"
    assert data["action"]["severity"] == "UNKNOWN"
    assert data["action"]["mode"] == "unknown"
    assert data["action"]["profile_present"] is True
    assert data["action"]["files_that_would_change_count"] == 1


def test_fix_cleans_backup_root_if_target_write_fails(tmp_path, monkeypatch):
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    original_open = Path.open

    def failing_open(self, *args, **kwargs):
        if self == hermes_home / "config.yaml":
            raise OSError("simulated config write failure")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="simulated config write failure"):
        build_fix_preview(sample_plan(), "rp-0001", hermes_home=hermes_home, execute=True)
    assert not (hermes_home / "config.yaml").exists()
    assert not (hermes_home / ".hermes-system-doctor-backups").exists()


def test_fix_preserves_preexisting_empty_backup_root_if_target_write_fails(tmp_path, monkeypatch):
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    backup_root = hermes_home / ".hermes-system-doctor-backups"
    backup_root.mkdir()
    original_open = Path.open

    def failing_open(self, *args, **kwargs):
        if self == hermes_home / "config.yaml":
            raise OSError("simulated config write failure")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="simulated config write failure"):
        build_fix_preview(sample_plan(), "rp-0001", hermes_home=hermes_home, execute=True)
    assert not (hermes_home / "config.yaml").exists()
    assert backup_root.exists()
    assert list(backup_root.iterdir()) == []


def test_fix_blocks_without_explicit_hermes_home_for_registered_executor(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")
    result = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0001")
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["status"] == "BLOCKED_HERMES_HOME_REQUIRED"


def test_fix_blocks_symlink_targets_and_invalid_parents_without_backup_side_effects(tmp_path):
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "preview.json"
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")

    symlink_home = tmp_path / "symlink-home"
    symlink_home.mkdir()
    outside = tmp_path / "outside-config.yaml"
    (symlink_home / "config.yaml").symlink_to(outside)
    symlink_result = run_cli(
        "fix",
        "--hermes-home",
        str(symlink_home),
        "--plan",
        str(plan_path),
        "--approve",
        "rp-0001",
        "--execute",
        "--output",
        str(output_path),
    )
    assert symlink_result.returncode == 2
    symlink_data = json.loads(output_path.read_text(encoding="utf-8"))
    assert symlink_data["status"] == "BLOCKED_UNSAFE_TARGET"
    assert not outside.exists()
    assert not (symlink_home / ".hermes-system-doctor-backups").exists()

    bad_parent_plan = sample_plan()
    bad_parent_plan["actions"][0]["profile"] = "operator"
    bad_parent_plan_path = tmp_path / "bad-parent-plan.json"
    bad_parent_output = tmp_path / "bad-parent-preview.json"
    bad_parent_plan_path.write_text(json.dumps(bad_parent_plan), encoding="utf-8")
    bad_parent_home = tmp_path / "bad-parent-home"
    bad_parent_home.mkdir()
    (bad_parent_home / "profiles").write_text("not a directory", encoding="utf-8")
    bad_parent_result = run_cli(
        "fix",
        "--hermes-home",
        str(bad_parent_home),
        "--plan",
        str(bad_parent_plan_path),
        "--approve",
        "rp-0001",
        "--execute",
        "--output",
        str(bad_parent_output),
    )
    assert bad_parent_result.returncode == 2
    bad_parent_data = json.loads(bad_parent_output.read_text(encoding="utf-8"))
    assert bad_parent_data["status"] == "BLOCKED_UNSAFE_TARGET"
    assert not (bad_parent_home / ".hermes-system-doctor-backups").exists()


def test_fix_markdown_preview_is_safe(tmp_path):
    plan_path = tmp_path / "plan.json"
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")
    result = run_cli(
        "fix",
        "--hermes-home",
        str(hermes_home),
        "--plan",
        str(plan_path),
        "--approve",
        "rp-0001",
        "--markdown",
    )
    assert result.returncode == 0
    assert "Hermes Agent System Doctor Fix Preview" in result.stdout
    assert "Status: `DRY_RUN_READY`" in result.stdout
    assert "Backup performed: `false`" in result.stdout
    assert_no_traps(result.stdout)
