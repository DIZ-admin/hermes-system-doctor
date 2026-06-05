import json
import subprocess
import sys

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
    marker = hermes_home / "config.yaml"
    marker.write_text("model:\n  provider: test\n", encoding="utf-8")
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")

    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    result = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0001", "--output", str(output_path))
    assert result.returncode == 0, result.stderr
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert after == before | {output_path.relative_to(tmp_path)}
    assert marker.read_text(encoding="utf-8") == "model:\n  provider: test\n"

    payload = output_path.read_text(encoding="utf-8")
    assert_no_traps(payload)
    data = json.loads(payload)
    assert data["status"] == "DRY_RUN_READY"
    assert data["dry_run"] is True
    assert data["execute_requested"] is False
    assert data["side_effects_performed"] == []
    assert data["backup"]["required"] is True
    assert data["backup"]["performed"] is False
    assert data["diff"]["available"] is False
    assert data["action"]["action_id"] == "rp-0001"


def test_fix_execute_is_blocked_until_executor_exists(tmp_path):
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "execute-preview.json"
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    marker = hermes_home / "config.yaml"
    marker.write_text("model:\n  provider: test\n", encoding="utf-8")
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")

    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    result = run_cli(
        "fix",
        "--plan",
        str(plan_path),
        "--approve",
        "rp-0001",
        "--execute",
        "--output",
        str(output_path),
    )
    assert result.returncode == 2
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert after == before | {output_path.relative_to(tmp_path)}
    assert marker.read_text(encoding="utf-8") == "model:\n  provider: test\n"
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["status"] == "BLOCKED_NO_EXECUTOR"
    assert data["execute_requested"] is True
    assert data["side_effects_performed"] == []
    assert data["backup"]["performed"] is False


def test_fix_blocks_diagnostic_only_and_missing_actions(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")

    diagnostic = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0002")
    assert diagnostic.returncode == 1
    diagnostic_data = json.loads(diagnostic.stdout)
    assert diagnostic_data["status"] == "BLOCKED_DIAGNOSTIC_ONLY"
    assert diagnostic_data["backup"]["required"] is False

    missing = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-9999")
    assert missing.returncode == 1
    missing_data = json.loads(missing.stdout)
    assert missing_data["status"] == "BLOCKED_ACTION_NOT_FOUND"


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
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    assert data["action"]["component"] == "unknown"
    assert data["action"]["severity"] == "UNKNOWN"
    assert data["action"]["mode"] == "unknown"
    assert data["action"]["profile_present"] is True
    assert data["action"]["files_that_would_change_count"] == 1


def test_fix_markdown_preview_is_safe(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(sample_plan()), encoding="utf-8")
    result = run_cli("fix", "--plan", str(plan_path), "--approve", "rp-0001", "--markdown")
    assert result.returncode == 0
    assert "Hermes Agent System Doctor Fix Preview" in result.stdout
    assert "Status: `DRY_RUN_READY`" in result.stdout
    assert "Backup performed: `false`" in result.stdout
    assert_no_traps(result.stdout)
