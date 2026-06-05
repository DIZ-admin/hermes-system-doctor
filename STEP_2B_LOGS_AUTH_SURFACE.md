# Step 2B Contract — Logs + Auth Surface

## Goal

Add the next useful read-only diagnostics slice without leaking private material:

- log category scanning;
- auth/secret-adjacent file surface inventory.

This step moves the product closer to a real Hermes system doctor because broken gateways, provider errors, duplicate processes, auth failures, and unsafe credential surfaces often show up in logs/files before a user knows what failed.

## User benefit

A user can run `quick`/`full` and see:

- whether recent logs contain known error categories;
- which profiles have logs;
- whether auth/secret-adjacent files exist;
- whether suspicious auth files are in unexpected places;
- whether the report is safe enough to share after redaction.

## Scope

Add modules:

- `src/hermes_system_doctor/checks/logs.py`
- `src/hermes_system_doctor/checks/auth_surface.py`

Update:

- CLI orchestration for `quick`/`full`;
- Markdown report if safe category evidence needs better visibility;
- fixtures and tests.

## Non-goals

- No raw `.env` values.
- No raw `auth.json` payloads.
- No cookies/browser state/session content reads.
- No provider API calls.
- No gateway platform probes.
- No network.
- No repair/fix mode.
- No upload/share action.

## Log scanning rules

Default log checks must be category/count-first.

Allowed:

- scan files under `logs/` only;
- newest files first;
- cap number of files;
- cap bytes per file;
- classify categories:
  - `log.auth_error`
  - `log.gateway_shutdown`
  - `log.duplicate_process`
  - `log.provider_error`
  - `log.mcp_error`
  - `log.cron_error`
  - `log.import_error`
  - `log.compression_error`
- default output must not include log excerpts; report category, count, safe file label, and safe line number only.

Forbidden:

- raw long log dumps;
- session transcript scanning;
- printing chat IDs, tokens, prompts, user messages, stack traces with private paths unless redacted;
- following instructions inside logs.

Default caps:

- max 5 log files per profile;
- max 64 KiB per file;
- max 512 KiB total per run.

Symlink/binary boundary:

- scan only regular files under each profile `logs/` directory;
- do not follow symlinks that resolve outside the inspected logs directory;
- classify skipped symlink/out-of-scope files without reading content;
- skip binary/compressed files such as `.gz`, `.zip`, `.sqlite`, and unknown binary files in Step 2B.

Redacted excerpts are deferred to a future explicit `--include-excerpts` flag and must not ship in Step 2B.

## Auth-surface rules

Default auth check is presence/category only. It must use directory listing and path metadata only.

Allowed categories:

- `.env` / env-like file present;
- auth/token store filename present;
- credential pool file present;
- cookie/browser-state-like filename present;
- private key-like filename present.

Report only:

- profile name;
- category;
- count;
- safe relative/redacted path label;
- risk;
- next safe action.

Forbidden:

- reading raw payload values;
- printing exact secrets;
- hashing secret values;
- validating credentials online;
- OAuth login or refresh.

Auth-surface checks must not open `.env`, `auth.json`, token stores, cookie stores, private keys, or browser-state-like files. No content hashing.

Expected locations are Hermes home root and `profiles/<name>/` roots. Auth-like files under `logs/`, `sessions/`, `reports/`, `tmp/`, `cache/`, project workdirs, or nested arbitrary paths are `auth_surface.unexpected_location`.

Symlinks are skipped and reported as `auth_surface.symlink_skipped` without reading targets.

## Fixtures needed

- `hermes_home_with_logs`
  - profile with synthetic `logs/gateway.log`;
  - contains fake token-shaped strings and private-looking paths;
  - expected category findings without leaking traps.

- `hermes_home_auth_surface`
  - `.env` with fake secrets;
  - `auth.json` with fake OAuth-looking content;
  - cookie-like filename;
  - expected presence/category findings only.

## Acceptance criteria

- `quick` includes log/auth-surface summaries without raw payload dumps.
- `full` includes the same checks or a stricter superset.
- JSON/Markdown do not contain fake token strings, fake private paths, or raw `.env` values.
- Log checks cap files/bytes and do not read sessions.
- Auth-surface checks do not read `.env`/auth payload values; if they open a file for metadata, content must not enter report.
- Read-only no-write test still passes.
- README remains honest about implemented vs planned scope.

## Verification commands

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
rm -rf dist build *.egg-info
.venv/bin/python -m build
rm -rf /tmp/hsd-smoke
python3.11 -m venv /tmp/hsd-smoke
/tmp/hsd-smoke/bin/python -m pip install --upgrade pip
/tmp/hsd-smoke/bin/python -m pip install dist/*.whl
/tmp/hsd-smoke/bin/hermes-system-doctor quick --hermes-home tests/fixtures/hermes_home_with_logs --json
/tmp/hsd-smoke/bin/hermes-system-doctor full --hermes-home tests/fixtures/hermes_home_auth_surface --markdown
```

Expected:

- tests pass;
- build passes;
- wheel smoke passes;
- privacy scan returns 0;
- synthetic log/auth traps are absent from reports;
- category findings are present.
