# Hermes Agent System Doctor

Diagnostics and approval-gated repair planning for [Hermes Agent](https://github.com/NousResearch/hermes-agent) installations.

Hermes Agent System Doctor is being built as a discovery-first companion to the stock `hermes doctor`. Stock `hermes doctor` checks the base install; this tool is meant to map the wider local Hermes system and separate **fact**, **risk**, **unknown**, and **approval-required repair**.

## Status

Early safety-first preview. Diagnostic modes are read-only; `fix --execute` is approval-gated and limited to registered narrow executors. Current implementation covers:

- Hermes home discovery;
- root + named profile inventory;
- `config.yaml` existence and YAML parseability;
- gateway config/log/PID signals without service restart or platform probes;
- cron metadata parsing;
- missing cron script/workdir detection;
- log category scanning without raw log excerpts;
- auth/secret-adjacent file presence inventory without reading payloads;
- memory surface inventory without dumping memory content;
- skills integrity checks without dumping skill bodies;
- plugins inventory without executing plugin code;
- MCP server config checks without connecting to servers or running tools;
- post-update drift signals from local logs and local git metadata without network fetch;
- repair-plan generation from a JSON report without applying fixes;
- gated fix mode with `--approve action-id`, backup manifest, diff preview, rollback hint, and one narrow registered executor for `config.missing`;
- safe JSON/Markdown reports;
- redaction tests and read-only tests.

Planned but not implemented yet:

- additional registered fix executors for specific findings after backup/diff/rollback semantics are proven per executor.

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
hermes-system-doctor repair-plan --input report.json --output repair-plan.json
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001 --output fix-preview.json
```

Note: `quick` runs the current safe core checks. `full` and `post-update` also include local post-update drift diagnostics. `fix` is approval-gated and intentionally narrow: the only registered mutating executor currently creates a minimal parseable `config.yaml` stub for `config.missing` after writing a backup manifest. Other repair candidates remain preview-only or blocked.

## Core safety promise

Diagnostic modes are read-only and offline; gated `fix --execute` is the only mode that can write, and only for registered narrow executors:

- no config writes in diagnostic or repair-plan modes;
- no gateway restart;
- no gateway platform probes;
- no cron execution;
- no plugin execution;
- no MCP tool execution;
- no platform messages;
- no network probes;
- no repair execution in `repair-plan` mode;
- `fix --execute` can write only through registered narrow executors; current executor writes a backup manifest and a minimal `config.yaml` stub for `config.missing` only;
- no raw secrets in reports.

## Canonical source

This project is maintained by Aleksei Ulianov / Sprut_AI.
Original repository: https://github.com/AlekseiUL/hermes-system-doctor

If you found this project mirrored, repackaged, or redistributed elsewhere, check this repository as the source of truth.

## Attribution

Where permitted by the applicable license, if you reuse, fork, modify, package, or publish this work, keep the original copyright and license notice and link back to the canonical repository.
