# Quality Loop — Hermes Agent System Doctor

This product is built in small verified steps. Every step must be reviewed through three lenses before it is called done.

## Roles

- Product/architecture review: confirms the feature is useful, clear, safe, and not pretending to replace stock `hermes doctor`.
- Implementation review: confirms the repo structure, CLI behavior, tests, packaging, and smoke path are practical.
- Reliability gate: confirms root cause, safety boundaries, redaction, read-only behavior, test output, and release hygiene.

Public repo language should stay generic: these are review lenses, not product surface.

## Step contract

Each implementation step must define:

1. Goal — what user benefit the step adds.
2. Scope — exact files/modules/commands touched.
3. Non-goals — what the step must not do.
4. Safety boundary — secrets, writes, network, service restarts, platform actions.
5. Fixtures — synthetic Hermes homes used for tests.
6. Verification — exact commands and expected outputs.
7. Review — product/architecture + implementation feedback before marking the step done.
8. Done report — facts, risks left, next step.

## Default safety policy

Default runs are read-only and offline.

Allowed by default:

- read synthetic fixtures;
- read local Hermes metadata when a user explicitly points `--hermes-home` at it;
- parse config/log metadata with redaction;
- write an explicit `--output` report path;
- print redacted summaries.

Forbidden by default:

- edit config;
- migrate config;
- restart gateway;
- run cron;
- execute MCP tools;
- send platform messages;
- call external APIs;
- read raw `.env`, `auth.json`, cookies, browser state, session payloads, or memory contents into reports;
- mark unproven platform/provider health as green.

## Required checks before each commit

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
rm -rf dist build *.egg-info
.venv/bin/python -m build
python -m venv /tmp/hsd-smoke
/tmp/hsd-smoke/bin/python -m pip install --upgrade pip
/tmp/hsd-smoke/bin/python -m pip install dist/*.whl
/tmp/hsd-smoke/bin/hermes-system-doctor discover --hermes-home tests/fixtures/hermes_home_minimal --json
```

Plus privacy scan:

- no private operator paths;
- no internal profile/team names;
- no bytecode;
- no staged secrets;
- no raw `.env`/auth/session payloads in fixtures or reports.

## Release rule

No GitHub push/release is done until:

- local checks pass;
- privacy scan passes;
- product/architecture review passes;
- implementation review passes;
- final smoke install from built artifact passes.
