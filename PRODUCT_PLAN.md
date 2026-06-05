# Product Plan — Hermes Agent System Doctor

## Verdict

Build as a standalone read-only companion CLI for Hermes Agent installations.

The differentiator is not “another doctor command”. It is **discovery-first system mapping** across profiles, gateway, cron, memory, skills, plugins, MCP, logs, and post-update drift.

## Product line

> Stock `hermes doctor` checks the base install. Hermes Agent System Doctor maps the whole local Hermes system and shows what changed, what is broken, what is unknown, and what not to touch without approval.

## MVP commands

```bash
hermes-system-doctor discover
hermes-system-doctor quick
hermes-system-doctor full
hermes-system-doctor post-update
hermes-system-doctor report --input report.json --format markdown
```

Alias:

```bash
hsd quick
hsd full --profile work
```

## MVP scope

- Environment inventory: OS, Python, Hermes CLI path/version, active `HERMES_HOME`/profile signals.
- Profile discovery: root profile + named profiles under `profiles/`.
- Config checks: existence, parseability, unknown/deprecated keys where rules exist.
- Gateway checks: config/log/process signals; no platform calls by default.
- Cron checks: metadata parse, enabled/paused counts, missing script/workdir references.
- Memory checks: provider presence, file/DB metadata, size pressure; no raw memory dump by default.
- Skills checks: count, duplicate names, frontmatter, missing linked files, huge files.
- Plugins checks: enabled/installed manifests and missing command/env presence by name only.
- MCP checks: configured servers, command/url shape, missing executable/env names; reachability only with explicit network flag later.
- Logs checks: capped, redacted category matching.
- Post-update drift: version/source drift, stale process hints, import errors after update, config compatibility warnings.
- JSON + Markdown reports.

## Non-goals for MVP

- No autofix.
- No writes except explicit `--output` report path.
- No service restart.
- No cron execution.
- No OAuth login.
- No gateway platform probes by default.
- No raw `.env`, `auth.json`, cookies, sessions, memory, or logs in reports.
- No private topology, roster, Kanban, wiki, or internal agent assumptions.

## Severity model

- `OK`: confirmed healthy or informational.
- `WARN`: likely issue or hygiene risk.
- `FAIL`: confirmed broken local component.
- `UNKNOWN`: cannot prove safely without network, credentials, platform action, or user approval.
- `NEEDS_APPROVAL`: next action has side effects.

Each finding must include:

- component;
- profile if applicable;
- fact/evidence;
- risk;
- next safe diagnostic command;
- whether approval is required.

## Release gates

1. Redaction tests catch fake API keys, OAuth tokens, bot tokens, cookies, chat IDs, `.env`, `auth.json`, and session-like content.
2. Default mode is read-only and offline; tests must prove no writes except explicit report output.
3. Synthetic fixture coverage for single profile, multi-profile, cron issue, MCP issue, broken skill, memory pressure, post-update drift.
4. JSON schema stable enough for automation.
5. Markdown report useful to a normal Hermes user without private context.
6. Public repo scan has no private paths, local agent names, secrets, bytecode, or generated artifacts.
7. CI passes on Linux and macOS; WSL documented as supported target after smoke.
8. README states this is an independent companion, not an official Hermes component.

## Product risks

- Secret leakage if redaction is weak.
- False confidence if unknown checks are marked green.
- Upstream brand friction if positioned as a replacement for Hermes doctor.
- Support burden if reports do not include exact next safe commands.
- Drift with Hermes releases if parsers are brittle.

## Recommended repo/package

- Repository: `hermes-system-doctor`
- Package: `hermes-system-doctor`
- Python import: `hermes_system_doctor`
- Console scripts: `hermes-system-doctor`, `hsd`
