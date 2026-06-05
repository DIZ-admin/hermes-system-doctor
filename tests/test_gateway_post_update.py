import json
import os
import subprocess
import sys

TRAPS = [
    "LEAK_TRAP_GATEWAY_LOG_RAW",
    "LEAK_TRAP_MEDIA_PATH_RAW",
    "LEAK_TRAP_IMPORT_RAW",
    "LEAK_TRAP_UPDATE_RAW",
]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "hermes_system_doctor.cli", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def check_by_name(data: dict, name: str) -> dict:
    return next(check for check in data["checks"] if check["name"] == name)


def assert_no_traps(output: str):
    for trap in TRAPS:
        assert trap not in output


def test_gateway_reports_config_pid_and_log_signals_without_raw_log_text(tmp_path):
    home = tmp_path / "hermes"
    logs = home / "logs"
    logs.mkdir(parents=True)
    (home / "config.yaml").write_text(
        "platforms:\n"
        "  telegram:\n"
        "    enabled: true\n"
        "  discord:\n"
        "    enabled: false\n",
        encoding="utf-8",
    )
    (home / "gateway.pid").write_text("99999999\n", encoding="utf-8")
    (logs / "gateway.log").write_text(
        "Starting Hermes Gateway LEAK_TRAP_GATEWAY_LOG_RAW\n"
        "Received SIGTERM LEAK_TRAP_GATEWAY_LOG_RAW\n"
        "Skipping unsafe MEDIA directive path outside allowed roots LEAK_TRAP_MEDIA_PATH_RAW\n"
        "Message to edit not found LEAK_TRAP_GATEWAY_LOG_RAW\n",
        encoding="utf-8",
    )
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    gateway = check_by_name(data, "gateway")
    ids = {finding["id"] for finding in gateway["findings"]}
    assert "gateway.pid_stale_or_unreadable" in ids
    assert "gateway.sigterm_seen" in ids
    assert "gateway.media_block_seen" in ids
    assert "gateway.send_error_seen" in ids
    assert gateway["facts"]["configured_platforms"] == {"default": ["telegram"]}
    assert gateway["facts"]["platform_probes"] == "not_run"
    assert gateway["facts"]["service_restarts"] == "not_run"
    assert gateway["facts"]["messages_sent"] == "not_run"


def test_gateway_accepts_json_pid_file_when_process_exists(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("platforms: []\n", encoding="utf-8")
    (home / "gateway.pid").write_text(
        json.dumps({"pid": os.getpid(), "kind": "hermes-gateway"}) + "\n",
        encoding="utf-8",
    )

    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    gateway = check_by_name(data, "gateway")
    ids = {finding["id"] for finding in gateway["findings"]}
    assert "gateway.pid_stale_or_unreadable" not in ids
    assert gateway["facts"]["pid_files"] == {"default:gateway.pid": "running"}


def test_gateway_symlink_log_is_skipped_without_following_target(tmp_path):
    home = tmp_path / "hermes"
    logs = home / "logs"
    outside = tmp_path / "outside"
    logs.mkdir(parents=True)
    outside.mkdir()
    (home / "config.yaml").write_text("platforms: []\n", encoding="utf-8")
    (outside / "gateway.log").write_text("Received SIGTERM LEAK_TRAP_GATEWAY_LOG_RAW\n", encoding="utf-8")
    (logs / "gateway.log").symlink_to(outside / "gateway.log")
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_GATEWAY_LOG_RAW" not in result.stdout
    data = json.loads(result.stdout)
    gateway = check_by_name(data, "gateway")
    ids = {finding["id"] for finding in gateway["findings"]}
    assert "gateway.log_skipped" in ids


def test_post_update_drift_scans_logs_and_git_metadata_without_network_or_imports(tmp_path):
    home = tmp_path / "hermes"
    logs = home / "logs"
    source = home / "hermes-agent"
    git = source / ".git"
    logs.mkdir(parents=True)
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "refs" / "remotes" / "origin").mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (logs / "agent.log").write_text(
        "ModuleNotFoundError: No module named private_module LEAK_TRAP_IMPORT_RAW\n"
        "version mismatch after update LEAK_TRAP_UPDATE_RAW\n"
        "pid file race lost LEAK_TRAP_UPDATE_RAW\n",
        encoding="utf-8",
    )
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text("1" * 40 + "\n", encoding="utf-8")
    (git / "refs" / "remotes" / "origin" / "main").write_text("2" * 40 + "\n", encoding="utf-8")
    result = run_cli("post-update", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    drift = check_by_name(data, "post_update_drift")
    ids = {finding["id"] for finding in drift["findings"]}
    assert "post_update.import_error" in ids
    assert "post_update.version_mismatch" in ids
    assert "post_update.stale_process_hint" in ids
    assert "post_update.local_origin_ref_differs" in ids
    assert drift["facts"]["git_network_fetch"] == "not_run"
    assert drift["facts"]["dependency_imports"] == "not_run"
    assert drift["facts"]["service_restarts"] == "not_run"


def test_quick_excludes_post_update_drift_but_full_includes_it(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    quick = run_cli("quick", "--hermes-home", str(home), "--json")
    full = run_cli("full", "--hermes-home", str(home), "--json")
    assert quick.returncode == 0
    assert full.returncode == 0
    quick_names = {check["name"] for check in json.loads(quick.stdout)["checks"]}
    full_names = {check["name"] for check in json.loads(full.stdout)["checks"]}
    assert "gateway" in quick_names
    assert "post_update_drift" not in quick_names
    assert "post_update_drift" in full_names
