import json
import subprocess
import sys

TRAPS = [
    "LEAK_TRAP_REPAIR_SECRET",
    "LEAK_TRAP_REPAIR_LOG_RAW",
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


def test_repair_plan_generates_dry_run_actions_without_applying_fixes(tmp_path):
    report = {
        "mode": "full",
        "status": "WARN",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "hermes_home": "[REDACTED_PATH]/hermes",
        "checks": [
            {
                "name": "config",
                "severity": "WARN",
                "summary": "profiles=1 findings=1",
                "facts": {},
                "findings": [
                    {
                        "id": "config.missing",
                        "severity": "WARN",
                        "component": "config",
                        "profile": "default",
                        "summary": "Profile config.yaml is missing LEAK_TRAP_REPAIR_SECRET",
                        "evidence": ["default"],
                        "risk": "Profile may be incomplete.",
                        "next_action": "Run hermes config path to verify.",
                    }
                ],
            },
            {
                "name": "gateway",
                "severity": "WARN",
                "summary": "gateway finding",
                "facts": {},
                "findings": [
                    {
                        "id": "gateway.sigterm_seen",
                        "severity": "WARN",
                        "component": "gateway",
                        "summary": "Gateway log signal matched LEAK_TRAP_REPAIR_LOG_RAW",
                        "evidence": ["logs/gateway.log", "line=1"],
                        "risk": "Gateway lifecycle signal.",
                        "next_action": "Inspect local gateway log.",
                    }
                ],
            },
            {
                "name": "auth_surface",
                "severity": "WARN",
                "summary": "auth finding",
                "facts": {},
                "findings": [
                    {
                        "id": "auth_surface.env_file",
                        "severity": "WARN",
                        "component": "auth_surface",
                        "summary": "Auth surface found",
                        "evidence": ["LEAK_TRAP_REPAIR_SECRET raw token-like evidence"],
                        "risk": "Auth surface exists.",
                        "next_action": "systemctl restart hermes-gateway && rm -rf ~/.hermes",
                    }
                ],
            },
            {
                "name": "unknown",
                "severity": "WARN",
                "summary": "unknown finding",
                "facts": {},
                "findings": [
                    {
                        "id": "evil; rm -rf ~/.hermes",
                        "severity": "WARN",
                        "component": "unknown_component",
                        "summary": "Unknown component",
                        "evidence": [],
                        "risk": "Unknown risk.",
                    }
                ],
            },
        ],
    }
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "repair-plan.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    before = set(tmp_path.iterdir())
    result = run_cli("repair-plan", "--input", str(report_path), "--output", str(output_path))
    assert result.returncode == 0, result.stderr
    after = set(tmp_path.iterdir())
    assert after == before | {output_path}
    payload = output_path.read_text(encoding="utf-8")
    assert_no_traps(payload)
    plan = json.loads(payload)
    assert plan["dry_run_only"] is True
    assert len(plan["actions"]) == 4
    assert all(action["approval_required"] is True for action in plan["actions"])
    config_action = next(action for action in plan["actions"] if action["finding_id"] == "config.missing")
    gateway_action = next(action for action in plan["actions"] if action["finding_id"] == "gateway.sigterm_seen")
    auth_action = next(action for action in plan["actions"] if action["finding_id"] == "auth_surface.env_file")
    unknown_action = next(action for action in plan["actions"] if action["component"] == "unknown_component")
    assert config_action["mode"] == "approval_gated_repair_candidate"
    assert config_action["backup_required"] is True
    assert gateway_action["mode"] == "manual_diagnostic"
    assert gateway_action["backup_required"] is False
    assert auth_action["mode"] == "approval_gated_repair_candidate"
    assert auth_action["backup_required"] is True
    assert "restart" not in auth_action["manual_command"]
    assert "rm -rf" not in auth_action["manual_command"]
    assert auth_action["source_evidence"] == ["evidence_items=1"]
    assert "rm -rf" not in unknown_action["manual_command"]
    assert ";" not in unknown_action["finding_id"]
    assert all(action["destructive"] is False for action in plan["actions"])


def test_repair_plan_markdown_is_safe_and_requires_input(tmp_path):
    missing_input = run_cli("repair-plan")
    assert missing_input.returncode != 0
    report_path = tmp_path / "clean-report.json"
    report_path.write_text(
        json.dumps({"mode": "quick", "status": "OK", "checks": []}),
        encoding="utf-8",
    )
    result = run_cli("repair-plan", "--input", str(report_path), "--markdown")
    assert result.returncode == 0
    assert "Hermes Agent System Doctor Repair Plan" in result.stdout
    assert "No repair actions generated" in result.stdout
    assert "Dry-run only: `true`" in result.stdout


def test_repair_plan_from_real_doctor_report(tmp_path):
    home = tmp_path / "hermes"
    logs = home / "logs"
    logs.mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (logs / "gateway.log").write_text("Received SIGTERM LEAK_TRAP_REPAIR_LOG_RAW\n", encoding="utf-8")
    report_path = tmp_path / "report.json"
    plan_path = tmp_path / "plan.json"
    report = run_cli("full", "--hermes-home", str(home), "--json")
    assert report.returncode == 0
    report_path.write_text(report.stdout, encoding="utf-8")
    plan = run_cli("repair-plan", "--input", str(report_path), "--output", str(plan_path))
    assert plan.returncode == 0
    payload = plan_path.read_text(encoding="utf-8")
    assert "LEAK_TRAP_REPAIR_LOG_RAW" not in payload
    data = json.loads(payload)
    assert data["actions"]
    assert all(action["approval_required"] for action in data["actions"])
