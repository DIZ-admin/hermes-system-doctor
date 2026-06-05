# Step 2 Contract — Core Checks

## Goal

Make the product useful beyond scaffold by adding safe core diagnostics for a real Hermes installation shape:

- config parse;
- profile inventory;
- cron metadata;
- redacted log category scan;
- auth surface category inventory;
- stronger JSON/Markdown reports.

## User benefit

A user can run one command and understand:

- which profiles exist;
- which profile configs are parseable;
- whether cron metadata exists and references missing scripts/workdirs;
- whether recent logs contain common gateway/runtime error categories;
- whether secrets-adjacent files exist without exposing their values.

## Scope

Planned modules:

- migrate `src/hermes_system_doctor/checks.py` into a `checks/` package;
- `src/hermes_system_doctor/checks/discovery.py`
- `src/hermes_system_doctor/checks/config.py`
- `src/hermes_system_doctor/checks/profiles.py`
- `src/hermes_system_doctor/checks/cron.py`
- later batch: `logs.py`, `auth_surface.py`
- update CLI orchestration
- tests with synthetic fixtures only

First implementation batch is intentionally limited to discovery/config/profiles/cron. Logs and auth surface are delayed because they are the highest privacy-risk checks.

## Non-goals

- no `--fix`;
- no config writes;
- no gateway restart;
- no cron execution;
- no network/platform probes;
- no real user secrets/logs in fixtures;
- no private internal team topology.

## Safety details for Step 2

- Full absolute local paths must not appear in reports by default. Show paths relative to Hermes home, safe basenames, or `[REDACTED_PATH]`. Full paths require a future explicit `--show-paths` flag.
- Config checks must report existence, parseability, key presence, and schema/rule findings; they must not include raw config values. Secret-like keys are always `[REDACTED]`.
- Cron checks must not run jobs. Script/workdir evidence should be relative/redacted by default.
- Logs are not part of the first batch. When added later, default output should be category + count; raw snippets require strict cap and redaction tests.
- `UNKNOWN` is not green. Automation behavior must be documented and `--fail-on unknown` should be added before release if unknowns matter to CI.
- The CLI may default to `~/.hermes`, but the report must explicitly state that the local default Hermes home was inspected. Tests should mostly use explicit fixture `--hermes-home` paths.

## Fixtures needed

- `hermes_home_minimal` — one healthy root profile, expected `status=OK` for `discover`.
- `hermes_home_multi_profile` — root + named profiles, expected profiles count > 1, all configs parse.
- `hermes_home_with_cron_issue` — cron metadata with one missing script/workdir, expected finding ids `cron.script_missing` / `cron.workdir_missing`.
- `hermes_home_broken_config` — invalid YAML config, expected `config.parse_error`.
- Later batch: `hermes_home_with_logs` — synthetic logs with redaction traps and error categories.
- Later batch: `hermes_home_auth_surface` — fake `.env`/auth-like files where report must show category/presence only.

Redaction traps should include fake token-shaped strings, private-looking absolute paths, chat-id-like numbers, and auth filenames. The exact trap strings must never appear in JSON/Markdown output.

## Verification commands

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
rm -rf dist build *.egg-info
.venv/bin/python -m build
rm -rf /tmp/hsd-smoke
python -m venv /tmp/hsd-smoke
/tmp/hsd-smoke/bin/python -m pip install --upgrade pip
/tmp/hsd-smoke/bin/python -m pip install dist/*.whl
/tmp/hsd-smoke/bin/hermes-system-doctor quick --hermes-home tests/fixtures/hermes_home_multi_profile --json
/tmp/hsd-smoke/bin/hermes-system-doctor full --hermes-home tests/fixtures/hermes_home_with_cron_issue --markdown
```

Expected outputs:

- lint exits `0`;
- tests exit `0`;
- build creates wheel and sdist;
- `quick` on multi-profile fixture exits `0` and reports multiple profiles;
- `full` on cron issue fixture reports the expected cron findings and does not leak fake secret/path traps.

## Acceptance criteria

- JSON contains stable `mode`, `status`, `checks`, `findings`, and `facts` fields.
- Markdown and JSON reports do not contain fake secret strings, raw config values, or forbidden absolute path traps.
- `--fail-on warn`, `--fail-on fail`, and future `--fail-on unknown` behavior are covered by tests before public release.
- Default `quick`/`full` runs do not write inside Hermes home; only explicit `--output` may create a report file.
- Missing fixture/home path never returns false `OK`.
- `quick` returns useful profile/config/cron summaries.
- `full` includes all first-batch core checks.
- Missing script/workdir is classified as `WARN` or `FAIL` with exact safe next action.
- `.env`/auth files are never dumped.
- CLI exit codes remain predictable with `--fail-on`.
