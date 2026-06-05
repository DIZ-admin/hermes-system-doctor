import json
import subprocess
import sys

TRAPS = [
    "LEAK_TRAP_LOG_TOKEN",
    "LEAK_TRAP_PRIVATE_PATH",
    "LEAK_TRAP_ENV_VALUE",
    "LEAK_TRAP_AUTH_PAYLOAD",
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


def test_logs_check_reports_categories_without_raw_log_text():
    result = run_cli("quick", "--hermes-home", "tests/fixtures/hermes_home_with_logs", "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    checks = {check["name"]: check for check in data["checks"]}
    assert checks["logs"]["severity"] == "WARN"
    ids = {finding["id"] for finding in checks["logs"]["findings"]}
    assert "log.auth_error" in ids
    assert "log.provider_error" in ids
    assert "log.import_error" in ids
    assert "log.compression_error" in ids


def test_logs_markdown_has_category_evidence_without_traps():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_with_logs", "--markdown")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    assert "log.auth_error" in result.stdout
    assert "Evidence:" in result.stdout
    assert "gateway.log" in result.stdout


def test_auth_surface_reports_presence_without_payload_values():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_auth_surface", "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    checks = {check["name"]: check for check in data["checks"]}
    auth = checks["auth_surface"]
    assert auth["severity"] == "WARN"
    ids = {finding["id"] for finding in auth["findings"]}
    assert "auth_surface.env_file" in ids
    assert "auth_surface.auth_store" in ids
    assert "auth_surface.cookie_store_like" in ids
    assert "auth_surface.private_key_like" in ids
    assert "auth_surface.unexpected_location" in ids


def test_log_fact_keys_are_not_redacted():
    result = run_cli("quick", "--hermes-home", "tests/fixtures/hermes_home_with_logs", "--json")
    assert result.returncode == 0
    assert "skipped_files" in result.stdout
    assert "skipped_symlinks" in run_cli(
        "full", "--hermes-home", "tests/fixtures/hermes_home_auth_surface", "--json"
    ).stdout


def test_logs_symlink_directory_is_skipped_without_reading_target(tmp_path):
    home = tmp_path / "hermes"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside / "gateway.log").write_text("unauthorized 401 LEAK_TRAP_SYMLINK_TARGET\n", encoding="utf-8")
    (home / "logs").symlink_to(outside)
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_SYMLINK_TARGET" not in result.stdout
    data = json.loads(result.stdout)
    logs = next(check for check in data["checks"] if check["name"] == "logs")
    assert logs["facts"]["skipped_files"] == 1
    assert logs["facts"]["files_scanned"] == 0


def test_logs_symlink_file_is_skipped_without_reading_target(tmp_path):
    home = tmp_path / "hermes"
    outside = tmp_path / "outside"
    logs = home / "logs"
    home.mkdir()
    outside.mkdir()
    logs.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside / "evil.log").write_text("unauthorized 401 LEAK_TRAP_SYMLINK_FILE\n", encoding="utf-8")
    (logs / "evil.log").symlink_to(outside / "evil.log")
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_SYMLINK_FILE" not in result.stdout
    data = json.loads(result.stdout)
    logs_check = next(check for check in data["checks"] if check["name"] == "logs")
    assert logs_check["facts"]["skipped_files"] == 1
    assert logs_check["facts"]["files_scanned"] == 0


def test_symlinked_profile_directory_is_not_followed(tmp_path):
    home = tmp_path / "hermes"
    profiles = home / "profiles"
    outside = tmp_path / "outside-profile"
    outside_logs = outside / "logs"
    profiles.mkdir(parents=True)
    outside_logs.mkdir(parents=True)
    (outside / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside_logs / "gateway.log").write_text("unauthorized 401 LEAK_TRAP_PROFILE_SYMLINK\n", encoding="utf-8")
    (profiles / "external").symlink_to(outside)
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_PROFILE_SYMLINK" not in result.stdout
    data = json.loads(result.stdout)
    discovery = next(check for check in data["checks"] if check["name"] == "discovery")
    assert "external" not in discovery["facts"]["profiles"]


def test_profiles_root_symlink_is_not_followed(tmp_path):
    home = tmp_path / "hermes"
    outside_profiles = tmp_path / "outside-profiles"
    outside_logs = outside_profiles / "evil" / "logs"
    home.mkdir()
    outside_logs.mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside_profiles / "evil" / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside_logs / "gateway.log").write_text("unauthorized 401 LEAK_TRAP_PROFILES_ROOT_SYMLINK\n", encoding="utf-8")
    (home / "profiles").symlink_to(outside_profiles)
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_PROFILES_ROOT_SYMLINK" not in result.stdout
    data = json.loads(result.stdout)
    discovery = next(check for check in data["checks"] if check["name"] == "discovery")
    assert discovery["facts"]["profiles"] == ["default"]


def test_logs_total_byte_cap_is_strict(tmp_path):
    home = tmp_path / "hermes"
    logs = home / "logs"
    home.mkdir()
    logs.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    for index in range(9):
        (logs / f"{index}.log").write_text("unauthorized 401\n" + ("x" * 64980), encoding="utf-8")
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    data = json.loads(result.stdout)
    logs_check = next(check for check in data["checks"] if check["name"] == "logs")
    assert logs_check["facts"]["bytes_scanned"] <= 512 * 1024


def test_auth_surface_scans_home_root_even_without_config(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "auth.json").write_text('{"trap":"LEAK_TRAP_ROOT_AUTH"}\n', encoding="utf-8")
    result = run_cli("quick", "--hermes-home", str(home), "--json")
    assert "LEAK_TRAP_ROOT_AUTH" not in result.stdout
    data = json.loads(result.stdout)
    auth = next(check for check in data["checks"] if check["name"] == "auth_surface")
    ids = {finding["id"] for finding in auth["findings"]}
    assert "auth_surface.auth_store" in ids


def test_auth_surface_markdown_does_not_dump_payloads():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_auth_surface", "--markdown")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    assert "auth_surface.env_file" in result.stdout
    assert "auth_surface.auth_store" in result.stdout
    assert "not opened" not in result.stdout
