import json
import subprocess
import sys


def test_discover_fixture_json(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes_system_doctor.cli",
            "discover",
            "--hermes-home",
            str(home),
            "--json",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["mode"] == "discover"
    assert data["status"] == "OK"


def test_missing_home_fail_on_fail(tmp_path):
    missing = tmp_path / "missing"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes_system_doctor.cli",
            "quick",
            "--hermes-home",
            str(missing),
            "--fail-on",
            "fail",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "home.missing" in result.stdout
