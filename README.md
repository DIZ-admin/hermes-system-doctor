# Hermes Agent System Doctor

Read-only diagnostics for [Hermes Agent](https://github.com/NousResearch/hermes-agent) installations.

Hermes Agent System Doctor is being built as a discovery-first companion to the stock `hermes doctor`. Stock `hermes doctor` checks the base install; this tool is meant to map the wider local Hermes system and separate **fact**, **risk**, **unknown**, and **approval-required repair**.

## Status

Early read-only preview. Current implementation covers the first core slice only:

- Hermes home discovery;
- root + named profile inventory;
- `config.yaml` existence and YAML parseability;
- cron metadata parsing;
- missing cron script/workdir detection;
- log category scanning without raw log excerpts;
- auth/secret-adjacent file presence inventory without reading payloads;
- memory surface inventory without dumping memory content;
- skills integrity checks without dumping skill bodies;
- safe JSON/Markdown reports;
- redaction tests and read-only tests.

Planned but not implemented yet:

- gateway checks;
- plugins checks;
- MCP checks;
- post-update drift checks;
- repair planning / gated fix mode.

Do not treat the current preview as a complete system doctor or repair tool yet.

## Who is this for?

- Hermes users with one local profile who want a safe first health snapshot.
- Hermes users starting to run several profiles or cron jobs.
- Operators who want read-only diagnostics before touching services.

It is not an auto-repair tool, cloud scanner, official Hermes replacement, or support backdoor. It reports presence/risk of auth surfaces only; it does not validate whether credentials work.

## Requirements

- Python 3.10+
- Local Hermes Agent home, usually `~/.hermes`

## Preview quick start

```bash
uvx hermes-system-doctor quick --all-profiles --markdown --output hermes-system-report.md
```

During local development:

```bash
python -m pip install -e ".[dev]"
hermes-system-doctor discover --hermes-home tests/fixtures/hermes_home_minimal --json
pytest -q
```

## Current commands

```bash
hermes-system-doctor discover --json
hermes-system-doctor quick --all-profiles --markdown --output report.md
hermes-system-doctor full --json
hermes-system-doctor post-update --json
```

Note: `full` and `post-update` currently run the same first-slice checks as `quick`. Dedicated deep checks are planned.

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
