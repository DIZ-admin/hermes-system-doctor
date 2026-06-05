# Hermes Agent System Doctor

Read-only system diagnostics for [Hermes Agent](https://github.com/NousResearch/hermes-agent) installations.

Hermes Agent System Doctor inventories local Hermes profiles, config, gateway, cron, memory, skills, plugins, MCP, logs, and post-update drift, then produces a redacted report with safe next steps.

It complements the stock `hermes doctor`: stock doctor checks the base install; this tool maps the wider local Hermes system and separates **fact**, **risk**, **unknown**, and **approval-required repair**.

## Status

Early product scaffold. The first public release target is a read-only MVP with synthetic fixtures, redaction tests, JSON/Markdown reports, and no fix mode.

## Who is this for?

- Hermes users with one local profile who want a safe health snapshot.
- Hermes users running several profiles, gateways, cron jobs, skills, plugins, or MCP servers.
- Operators who want a post-update drift report before touching services.

It is not an auto-repair tool, cloud scanner, official Hermes replacement, or support backdoor.

## Planned quick start

```bash
uvx hermes-system-doctor quick --all-profiles --markdown --output hermes-system-report.md
```

During local development:

```bash
python -m pip install -e ".[dev]"
hermes-system-doctor discover --hermes-home tests/fixtures/hermes_home_minimal --json
pytest -q
```

## Core safety promise

Default mode is read-only and offline:

- no config writes;
- no gateway restart;
- no cron execution;
- no platform messages;
- no network probes;
- no raw secrets in reports.

## Canonical source

This project is maintained by Aleksei Ulianov / Sprut_AI.
Original repository: https://github.com/AlekseiUL/hermes-system-doctor

If you found this project mirrored, repackaged, or redistributed elsewhere, check this repository as the source of truth.

## Attribution

Where permitted by the applicable license, if you reuse, fork, modify, package, or publish this work, keep the original copyright and license notice and link back to the canonical repository.
