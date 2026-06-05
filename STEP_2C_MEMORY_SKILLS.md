# Step 2C Contract — Memory + Skills

## Goal

Add the next read-only diagnostics slice for Hermes installations:

- memory surface inventory without reading private memory content;
- skills integrity checks without dumping skill bodies;
- clear findings for pressure, malformed files, duplicate names, and missing linked files.

This moves the product closer to a real local agent-system doctor: profiles do not only have config/cron/logs; they accumulate memory and skills, and those layers can become stale, malformed, oversized, duplicated, or broken.

## Product value

A user should learn:

- whether memory files/stores exist for each profile;
- whether memory storage is becoming large enough to require cleanup/review;
- whether obvious memory metadata is malformed or unreadable;
- how many skills are installed;
- whether skills have valid frontmatter;
- whether two skills expose the same public `name`;
- whether linked files referenced by a skill are missing;
- which profile/component needs attention, without exposing private memories or skill content.

## Safety boundary

Default mode remains read-only and offline.

Forbidden:

- reading or printing raw memory content;
- printing raw skill bodies beyond safe metadata fields;
- reading sessions/transcripts as memory evidence;
- modifying memory, skills, configs, indexes, or caches;
- deleting duplicate skills;
- installing/updating/uninstalling skills;
- calling `hermes skills update/check/install`;
- running skill scripts;
- following symlinked skill or memory directories outside the inspected profile;
- following symlinked skill or memory files, `SKILL.md`, standalone skill markdown, or linked files;
- showing full absolute paths by default.

Allowed:

- file/directory metadata: exists, size, count, safe relative label;
- shallow parsing of skill frontmatter only;
- JSON/YAML parse validation for metadata/frontmatter;
- link existence checks for relative linked files explicitly declared in safe frontmatter metadata under the same skill directory;
- safe findings with `id`, severity, component, summary, risk, next_action, safe evidence.

## Memory check rules

Scan only known memory-surface names under each discovered profile root:

- `memories/`
- `memory/`
- `memory.json`
- `memory.db`
- `user.md`
- `USER.md`
- `MEMORY.md`

Do not recursively read arbitrary content. For Markdown/freeform memory files, use `lstat()`/`stat()` only: exists, type, size, and safe relative label. Do not read `USER.md`, `MEMORY.md`, `user.md`, or unknown memory stores. Structured metadata validation is allowed only for explicitly structured `memory.json`; for SQLite-like stores, use file metadata only in Step 2C. Never include sampled bytes in reports.

Severity guidance:

- `OK`: memory surface exists and is within limits, or no memory surface exists in a minimal profile.
- `WARN`: memory file/store is large, memory directory has many files, or metadata parse failed.
- `UNKNOWN`: memory provider is configured externally and local metadata is insufficient.
- `FAIL`: only for malformed structure that prevents safe inventory, not for large memory alone.

Initial thresholds:

- file warning: > 256 KiB;
- directory warning: > 200 files;
- total profile memory warning: > 2 MiB.

## Skills check rules

Scan only regular directories/files under profile `skills/`.

Recognized skill shapes:

- `<skills>/<category>/<skill>/SKILL.md`
- `<skills>/<skill>/SKILL.md`
- standalone `*.md` skill files only if they have YAML frontmatter with `name:`.

Do not follow symlinked skill roots, symlinked skill directories, symlinked `SKILL.md`, symlinked standalone skill markdown, or symlinked linked files.

Parse only bounded YAML frontmatter between leading `---` fences. Read at most 64 KiB / 400 lines from a skill markdown file to find the closing fence. If the closing fence is not found inside the bound, emit `skills.frontmatter_invalid` and do not scan the body.

Safe frontmatter metadata fields:

- `name`
- `description`
- `version`
- `tags`
- linked file references under `references/`, `templates/`, `scripts/`, `assets/` only when explicitly present in frontmatter metadata.

Linked-file checks are existence/type/symlink checks only. Do not read linked file contents and do not infer missing links from “obvious local directories” or skill body text.

Findings:

- `skills.frontmatter_missing`
- `skills.frontmatter_invalid`
- `skills.name_missing`
- `skills.duplicate_name`
- `skills.link_missing`
- `skills.symlink_skipped`
- `skills.too_many`

Do not report skill body text. Evidence must be safe relative labels only.

## Fixtures needed

- `hermes_home_with_memory_pressure`
  - large synthetic memory file with fake private trap text;
  - expected warning, no trap leak.
- `hermes_home_with_skills_ok`
  - one valid skill with linked files present.
- `hermes_home_with_skills_issues`
  - missing frontmatter;
  - invalid frontmatter;
  - duplicate skill names;
  - missing linked file;
  - symlinked skill dir pointing outside with leak trap.

## Acceptance criteria

- `quick` and `full` include `memory` and `skills` checks.
- No raw memory content appears in JSON/Markdown.
- No raw skill body appears in JSON/Markdown.
- Duplicate skill names are reported with safe evidence.
- Missing linked files are reported with safe evidence.
- Symlinked memory/skill files, directories, `SKILL.md`, and linked files are skipped and classified.
- Wheel contents do not include `tests/fixtures/**` or synthetic trap files; sdist may include fixtures for tests.
- Reports preserve stable JSON keys after redaction.
- All implemented README claims match code.

## Verification gate

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
rm -rf dist build *.egg-info
.venv/bin/python -m build
python3.11 -m venv /tmp/hsd-step2c-smoke
/tmp/hsd-step2c-smoke/bin/python -m pip install --upgrade pip
/tmp/hsd-step2c-smoke/bin/python -m pip install dist/*.whl
/tmp/hsd-step2c-smoke/bin/hermes-system-doctor full --hermes-home tests/fixtures/hermes_home_with_skills_issues --json
# unpack sdist and run tests there too
# privacy scan tracked tree + sdist + generated JSON/Markdown
```

## Non-goals

- No repair mode yet.
- No memory compaction.
- No skill install/update/delete.
- No semantic quality scoring of skill content.
- No reading session transcripts.
- No external registry checks.
