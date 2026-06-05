# Implementation Brief — Hermes Agent System Doctor

## Mission

Create a public-safe Python CLI repo for Hermes Agent diagnostics.

The product must be standalone, read-only by default, fixture-tested, and free of private team/runtime assumptions.

## Allowed implementation source

Use internal doctor work only as a pattern reference:

- mode split: `discover`, `quick`, `full`, `post-update`;
- dataclass/report aggregation model;
- severity model;
- category-only auth surface idea;
- redaction-first report discipline.

Do not copy private paths, profile names, team roster, Kanban contracts, wiki assumptions, prompts, live cron metadata, reports, memories, sessions, or logs.

## Phase 1 — public-safe scaffold

Implement:

- `pyproject.toml`;
- package under `src/hermes_system_doctor/`;
- CLI commands: `discover`, `quick`, `full`, `post-update`, `version`;
- models: `Finding`, `CheckResult`, `DoctorReport`;
- redaction module;
- discovery of Hermes home/root profiles using synthetic fixtures;
- JSON and Markdown report emitters;
- basic tests and CI.

Verification:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python -m build
python -m venv /tmp/hsd-smoke
/tmp/hsd-smoke/bin/pip install dist/*.whl
/tmp/hsd-smoke/bin/hermes-system-doctor discover --hermes-home tests/fixtures/hermes_home_minimal --json
```

## Phase 2 — core checks

Implement:

- config parse;
- profile inventory;
- cron metadata parse;
- redacted log category scan;
- auth surface category inventory;
- terminal/markdown/json report quality.

## Phase 3 — deeper checks

Implement:

- memory metadata;
- skills frontmatter/linked-file checks;
- plugin manifest checks;
- MCP config checks;
- post-update drift signals.

## Phase 4 — public release gate

Add:

- `LICENSE`, `NOTICE.md`, `SECURITY.md`;
- README EN first, RU section later;
- GitHub Actions;
- privacy scanner;
- synthetic example reports;
- release notes.

## Forbidden behavior

Default run must not:

- write inside Hermes home;
- edit config;
- read raw secret payloads;
- restart gateway;
- call external APIs;
- send platform messages;
- execute MCP tools;
- run cron jobs.

## First implementation task shape

Build only inside this repository. Use synthetic fixtures only. Return diff summary and real command outputs. If a check cannot be proven safely, classify it as `UNKNOWN`, not green.
