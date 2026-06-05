import json
import subprocess
import sys
from pathlib import Path

TRAPS = [
    "LEAK_TRAP_MEMORY_CONTENT",
    "LEAK_TRAP_MEMORY_JSON",
    "LEAK_TRAP_MEMORY_SYMLINK_TARGET",
    "LEAK_TRAP_SKILL_BODY_OK",
    "LEAK_TRAP_LINKED_FILE_OK",
    "LEAK_TRAP_SKILL_BODY_NO_FRONTMATTER",
    "LEAK_TRAP_SKILL_BODY_INVALID",
    "LEAK_TRAP_DUP_BODY_a",
    "LEAK_TRAP_DUP_BODY_b",
    "LEAK_TRAP_MISSING_LINK_BODY",
    "LEAK_TRAP_LINKED_SCRIPT_CONTENT",
    "LEAK_TRAP_OUTSIDE_SKILL",
    "LEAK_TRAP_SYMLINK_LINK_BODY",
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


def check_by_name(data: dict, name: str) -> dict:
    return next(check for check in data["checks"] if check["name"] == name)


def test_memory_pressure_reports_metadata_without_content():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_with_memory_pressure", "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    memory = check_by_name(data, "memory")
    ids = {finding["id"] for finding in memory["findings"]}
    assert "memory.file_large" in ids
    assert "memory.json_invalid" in ids
    assert memory["facts"]["surfaces_found"] >= 2


def test_memory_markdown_does_not_dump_memory_content():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_with_memory_pressure", "--markdown")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    assert "memory.file_large" in result.stdout


def test_skills_ok_is_clean_and_body_is_not_reported():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_with_skills_ok", "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    skills = check_by_name(data, "skills")
    assert skills["severity"] == "OK"
    assert skills["facts"]["skills_found"] == 1
    assert skills["facts"]["links_checked"] == 1


def test_skills_issues_are_reported_without_body_or_link_content():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_with_skills_issues", "--json")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    data = json.loads(result.stdout)
    skills = check_by_name(data, "skills")
    ids = {finding["id"] for finding in skills["findings"]}
    assert "skills.frontmatter_missing" in ids
    assert "skills.frontmatter_invalid" in ids
    assert "skills.duplicate_name" in ids
    assert "skills.link_missing" in ids


def test_skills_markdown_reports_safe_evidence_only():
    result = run_cli("full", "--hermes-home", "tests/fixtures/hermes_home_with_skills_issues", "--markdown")
    assert result.returncode == 0
    assert_no_traps(result.stdout)
    assert "skills.duplicate_name" in result.stdout
    assert "references/missing.md" in result.stdout


def test_skill_symlink_paths_are_skipped_without_reading_targets(tmp_path):
    home = tmp_path / "hermes"
    skills = home / "skills"
    outside = tmp_path / "outside-skill"
    outside_refs = outside / "references"
    skills.mkdir(parents=True)
    outside_refs.mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside / "SKILL.md").write_text(
        "---\nname: outside\ndescription: outside\n---\nLEAK_TRAP_DYNAMIC_SKILL_DIR_SYMLINK",
        encoding="utf-8",
    )
    (outside_refs / "secret.md").write_text("LEAK_TRAP_DYNAMIC_LINK_SYMLINK", encoding="utf-8")
    (skills / "outside").symlink_to(outside)
    linked = skills / "linked"
    (linked / "references").mkdir(parents=True)
    (linked / "SKILL.md").write_text(
        "---\nname: linked\ndescription: linked\nlinked_files:\n  references/secret.md: secret\n---\nbody",
        encoding="utf-8",
    )
    (linked / "references" / "secret.md").symlink_to(outside_refs / "secret.md")
    result = run_cli("full", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_DYNAMIC_SKILL_DIR_SYMLINK" not in result.stdout
    assert "LEAK_TRAP_DYNAMIC_LINK_SYMLINK" not in result.stdout
    data = json.loads(result.stdout)
    skills_check = check_by_name(data, "skills")
    ids = {finding["id"] for finding in skills_check["findings"]}
    assert "skills.symlink_skipped" in ids


def test_memory_symlink_file_is_not_followed(tmp_path):
    home = tmp_path / "hermes"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (outside / "memory.md").write_text("LEAK_TRAP_DYNAMIC_MEMORY_SYMLINK", encoding="utf-8")
    (home / "USER.md").symlink_to(outside / "memory.md")
    result = run_cli("full", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_DYNAMIC_MEMORY_SYMLINK" not in result.stdout
    data = json.loads(result.stdout)
    memory = check_by_name(data, "memory")
    ids = {finding["id"] for finding in memory["findings"]}
    assert "memory.symlink_skipped" in ids


def test_skill_frontmatter_bounded_without_body_leak(tmp_path):
    home = tmp_path / "hermes"
    skill_dir = home / "skills" / "huge"
    skill_dir.mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("---\nname: huge\n" + ("x" * (70 * 1024)) + "\nLEAK_TRAP_HUGE_BODY", encoding="utf-8")
    result = run_cli("full", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_HUGE_BODY" not in result.stdout
    data = json.loads(result.stdout)
    skills = check_by_name(data, "skills")
    ids = {finding["id"] for finding in skills["findings"]}
    assert "skills.frontmatter_invalid" in ids


def test_skill_link_outside_detection_preserves_raw_path_before_normalizing(tmp_path):
    home = tmp_path / "hermes"
    skill_dir = home / "skills" / "bad"
    skill_dir.mkdir(parents=True)
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: bad-links\n"
        "description: Bad links.\n"
        "linked_files:\n"
        "  ../secret.md: secret\n"
        "  /references/abs.md: abs\n"
        "  ./references/ok.md: ok\n"
        "---\n"
        "LEAK_TRAP_BAD_LINK_BODY",
        encoding="utf-8",
    )
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "ok.md").write_text("LEAK_TRAP_BAD_LINK_OK", encoding="utf-8")
    result = run_cli("full", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_BAD_LINK_BODY" not in result.stdout
    assert "LEAK_TRAP_BAD_LINK_OK" not in result.stdout
    data = json.loads(result.stdout)
    skills = check_by_name(data, "skills")
    outside = [finding for finding in skills["findings"] if finding["id"] == "skills.link_outside_skill"]
    assert len(outside) == 2
    evidence = "\n".join("\n".join(finding["evidence"]) for finding in outside)
    assert "../secret.md" in evidence
    assert "/references/abs.md" in evidence
    assert "./references/ok.md" not in evidence


def test_same_skill_name_in_different_profiles_is_not_duplicate(tmp_path):
    home = tmp_path / "hermes"
    for profile in ["a", "b"]:
        skill_dir = home / "profiles" / profile / "skills" / "dev" / "shared"
        skill_dir.mkdir(parents=True)
        (home / "profiles" / profile / "config.yaml").write_text(
            "model:\n  provider: test\n", encoding="utf-8"
        )
        (skill_dir / "SKILL.md").write_text(
            "---\nname: shared\ndescription: Shared name in isolated profile.\n---\nbody",
            encoding="utf-8",
        )
    result = run_cli("full", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    skills = check_by_name(data, "skills")
    ids = {finding["id"] for finding in skills["findings"]}
    assert "skills.duplicate_name" not in ids


def test_memory_case_variant_candidates_are_not_double_counted(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    (home / "USER.md").write_text("LEAK_TRAP_CASE_MEMORY\n" + ("x" * (260 * 1024)), encoding="utf-8")
    result = run_cli("full", "--hermes-home", str(home), "--json")
    assert result.returncode == 0
    assert "LEAK_TRAP_CASE_MEMORY" not in result.stdout
    data = json.loads(result.stdout)
    memory = check_by_name(data, "memory")
    assert memory["facts"]["surfaces_found"] == 1
    assert memory["facts"]["files"] == 1
    file_large = [finding for finding in memory["findings"] if finding["id"] == "memory.file_large"]
    assert len(file_large) == 1


def test_backward_compatible_check_aliases_import():
    from hermes_system_doctor.checks import discover_check, profile_config_check

    assert callable(discover_check)
    assert callable(profile_config_check)


def test_wheel_does_not_ship_fixtures_after_build():
    # This is intentionally lightweight; full build smoke runs in the gate.
    dist = Path("dist")
    if not dist.exists():
        return
    for wheel in dist.glob("*.whl"):
        assert "tests/fixtures" not in wheel.name
