from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from ..models import CheckResult, Finding, Severity
from ..path_utils import safe_relpath
from .discovery import profile_dirs

MAX_FRONTMATTER_BYTES = 64 * 1024
MAX_FRONTMATTER_LINES = 400
TOO_MANY_SKILLS = 200
ALLOWED_LINK_PREFIXES = ("references/", "templates/", "scripts/", "assets/")
LINK_KEYS = ("linked_files", "files", "references", "templates", "scripts", "assets")


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return False


def _read_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if _is_symlink(path):
        return None, "symlink"
    collected: list[bytes] = []
    total = 0
    try:
        with path.open("rb") as handle:
            first = handle.readline()
            total += len(first)
            if first.decode("utf-8", errors="replace").strip() != "---":
                return None, "missing"
            for _ in range(MAX_FRONTMATTER_LINES):
                line = handle.readline()
                if not line:
                    return None, "invalid"
                total += len(line)
                if total > MAX_FRONTMATTER_BYTES:
                    return None, "frontmatter_too_large"
                decoded = line.decode("utf-8", errors="replace")
                if decoded.strip() == "---":
                    raw = b"".join(collected).decode("utf-8", errors="replace")
                    try:
                        parsed = yaml.safe_load(raw) or {}
                    except yaml.YAMLError:
                        return None, "invalid"
                    if not isinstance(parsed, dict):
                        return None, "invalid"
                    return parsed, None
                collected.append(line)
    except OSError:
        return None, "read_failed"
    return None, "frontmatter_too_large"


def _skill_markdown_files(skills_root: Path) -> tuple[list[Path], int]:
    files: list[Path] = []
    skipped_symlinks = 0
    if not skills_root.exists():
        return files, skipped_symlinks
    if _is_symlink(skills_root) or not skills_root.is_dir():
        return files, 1 if _is_symlink(skills_root) else 0
    try:
        entries = sorted(skills_root.iterdir())
    except OSError:
        return files, skipped_symlinks
    for entry in entries:
        if _is_symlink(entry):
            skipped_symlinks += 1
            continue
        if entry.is_file() and entry.suffix.lower() == ".md":
            files.append(entry)
            continue
        if not entry.is_dir():
            continue
        skill_file = entry / "SKILL.md"
        if _is_symlink(skill_file):
            skipped_symlinks += 1
        elif skill_file.is_file():
            files.append(skill_file)
        try:
            subentries = sorted(entry.iterdir())
        except OSError:
            continue
        for child in subentries:
            if _is_symlink(child):
                skipped_symlinks += 1
                continue
            if child.is_dir():
                nested = child / "SKILL.md"
                if _is_symlink(nested):
                    skipped_symlinks += 1
                elif nested.is_file():
                    files.append(nested)
    return files, skipped_symlinks


def _extract_links(metadata: dict[str, Any]) -> list[str]:
    links: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, str):
            raw = value.strip()
            normalized = raw.lstrip("./")
            if raw.startswith(("/", "./", "../")) or normalized.startswith(ALLOWED_LINK_PREFIXES):
                links.append(raw)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)

    for key in LINK_KEYS:
        if key in metadata:
            visit(metadata[key])
    return sorted(set(links))


def _link_inside_skill(link: str) -> bool:
    raw = link.strip()
    if raw.startswith("/") or ".." in Path(raw).parts:
        return False
    return raw.lstrip("./").startswith(ALLOWED_LINK_PREFIXES)


def _normalized_link(link: str) -> str:
    return link.strip().lstrip("./")


def skills_check(hermes_home: Path) -> CheckResult:
    findings: list[Finding] = []
    facts = {
        "profiles_scanned": 0,
        "skills_found": 0,
        "frontmatter_ok": 0,
        "links_checked": 0,
        "symlinks_skipped": 0,
    }
    for profile_name, profile_path in profile_dirs(hermes_home):
        names: dict[str, list[str]] = defaultdict(list)
        facts["profiles_scanned"] += 1
        skills_root = profile_path / "skills"
        files, skipped = _skill_markdown_files(skills_root)
        facts["symlinks_skipped"] += skipped
        if skipped:
            findings.append(
                Finding(
                    id="skills.symlink_skipped",
                    severity="WARN",
                    component="skills",
                    profile=profile_name,
                    summary="Symlinked skill paths were skipped",
                    evidence=[safe_relpath(skills_root, hermes_home), f"skipped={skipped}"],
                    risk="A skill path may point outside the inspected Hermes profile.",
                    next_action="Inspect symlinked skill paths manually before trusting or cleaning them.",
                )
            )
        if len(files) > TOO_MANY_SKILLS:
            findings.append(
                Finding(
                    id="skills.too_many",
                    severity="WARN",
                    component="skills",
                    profile=profile_name,
                    summary="Profile has many skills installed",
                    evidence=[f"profile={profile_name} skills={len(files)}"],
                    risk="Large skill inventories can create noisy routing and slow review.",
                    next_action="Review skill inventory; do not delete automatically.",
                )
            )
        for skill_file in files:
            facts["skills_found"] += 1
            label = safe_relpath(skill_file, hermes_home)
            metadata, error = _read_frontmatter(skill_file)
            if error == "symlink":
                facts["symlinks_skipped"] += 1
                findings.append(
                    Finding(
                        id="skills.symlink_skipped",
                        severity="WARN",
                        component="skills",
                        profile=profile_name,
                        summary="Symlinked skill markdown was skipped",
                        evidence=[label],
                        risk="The skill file may point outside the inspected profile.",
                        next_action="Inspect the symlink manually before loading this skill.",
                    )
                )
                continue
            if error == "missing":
                findings.append(
                    Finding(
                        id="skills.frontmatter_missing",
                        severity="WARN",
                        component="skills",
                        profile=profile_name,
                        summary="Skill markdown is missing YAML frontmatter",
                        evidence=[label],
                        risk="Hermes may not be able to index or describe this skill reliably.",
                        next_action="Add safe YAML frontmatter with at least name and description.",
                    )
                )
                continue
            if error:
                findings.append(
                    Finding(
                        id="skills.frontmatter_invalid",
                        severity="WARN",
                        component="skills",
                        profile=profile_name,
                        summary="Skill frontmatter is invalid or too large to parse safely",
                        evidence=[label, f"error={error}"],
                        risk="Hermes may mis-index this skill, or the file may contain malformed metadata.",
                        next_action="Fix frontmatter after backing up the skill file.",
                    )
                )
                continue
            facts["frontmatter_ok"] += 1
            assert metadata is not None
            skill_name = metadata.get("name")
            if not isinstance(skill_name, str) or not skill_name.strip():
                findings.append(
                    Finding(
                        id="skills.name_missing",
                        severity="WARN",
                        component="skills",
                        profile=profile_name,
                        summary="Skill frontmatter is missing a valid name",
                        evidence=[label],
                        risk="Nameless skills are hard to route, update, or install cleanly.",
                        next_action="Add a stable lowercase skill name to frontmatter.",
                    )
                )
            else:
                names[skill_name.strip()].append(label)
            for link in _extract_links(metadata):
                facts["links_checked"] += 1
                if not _link_inside_skill(link):
                    findings.append(
                        Finding(
                            id="skills.link_outside_skill",
                            severity="WARN",
                            component="skills",
                            profile=profile_name,
                            summary="Skill frontmatter references a linked file outside allowed directories",
                            evidence=[label, link],
                            risk="A skill may point to unsafe or non-portable support files.",
                            next_action="Keep linked files under references/, templates/, scripts/, or assets/.",
                        )
                    )
                    continue
                normalized_link = _normalized_link(link)
                target = skill_file.parent / normalized_link
                if _is_symlink(target):
                    facts["symlinks_skipped"] += 1
                    findings.append(
                        Finding(
                            id="skills.symlink_skipped",
                            severity="WARN",
                            component="skills",
                            profile=profile_name,
                            summary="Symlinked linked file was skipped",
                            evidence=[label, link],
                            risk="A skill support file may point outside the inspected skill directory.",
                            next_action="Inspect the symlink manually before loading or publishing this skill.",
                        )
                    )
                    continue
                if not target.exists():
                    findings.append(
                        Finding(
                            id="skills.link_missing",
                            severity="WARN",
                            component="skills",
                            profile=profile_name,
                            summary="Skill frontmatter references a missing linked file",
                            evidence=[label, link],
                            risk="The skill may fail when it tries to load supporting files.",
                            next_action="Add the missing support file or remove the stale frontmatter reference.",
                        )
                    )
        for skill_name, labels in sorted(names.items()):
            if len(labels) > 1:
                findings.append(
                    Finding(
                        id="skills.duplicate_name",
                        severity="WARN",
                        component="skills",
                        profile=profile_name,
                        summary="Duplicate skill name found within one profile",
                        evidence=[f"name={skill_name}", *labels[:5]],
                        risk="Duplicate skill names inside one profile can cause routing ambiguity or update the wrong skill.",
                        next_action="Rename or consolidate duplicate skills in this profile after manual review.",
                    )
                )
    severity: Severity = "WARN" if findings else "OK"
    return CheckResult("skills", severity, f"skills={facts['skills_found']} links={facts['links_checked']}", findings, facts)
