import hashlib
import json
import subprocess
import sys
from pathlib import Path


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(root)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def test_quick_does_not_write_inside_hermes_home(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: test\n", encoding="utf-8")
    before = tree_digest(home)
    result = subprocess.run(
        [sys.executable, "-m", "hermes_system_doctor.cli", "quick", "--hermes-home", str(home), "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    json.loads(result.stdout)
    after = tree_digest(home)
    assert before == after
