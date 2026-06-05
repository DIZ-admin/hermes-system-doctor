# Hermes Agent System Doctor

Diagnostics and approval-gated repair planning for [Hermes Agent](https://github.com/NousResearch/hermes-agent) installations.

Stock `hermes doctor` checks the base install. **Hermes Agent System Doctor** maps the wider local Hermes system — profiles, gateway signals, cron metadata, logs, auth surfaces, memory, skills, plugins, MCP, and local post-update drift — then separates **fact**, **risk**, **unknown**, and **approval-required repair**.

It is built for operators who want proof before touching a live agent runtime.

## What it does now

Current implementation:

- discovers a Hermes home and root/named profiles;
- checks `config.yaml` existence and YAML parseability;
- reads gateway config/log/PID signals without service restart or platform probes;
- parses cron metadata without running jobs;
- detects missing cron script/workdir references;
- scans logs by category without raw log excerpts;
- inventories auth/secret-adjacent files without reading payloads;
- inventories memory surfaces without dumping memory content;
- checks skill metadata/frontmatter/linked-file integrity without dumping skill bodies;
- inventories plugins without executing plugin code;
- checks MCP server config shape without connecting to servers or running tools;
- reports local post-update drift signals without network fetch;
- generates dry-run repair plans from JSON reports;
- supports gated `fix --execute` for one narrow registered executor: `config.missing`;
- emits safe JSON and Markdown reports.

Planned next:

- additional registered fix executors, one finding at a time, only after backup/diff/rollback tests pass.

Do not treat the current preview as a complete universal repair tool.

## Who is this for?

- Hermes users who want a safe health snapshot before editing config or restarting anything.
- Operators running several Hermes profiles, cron jobs, skills, plugins, or MCP servers.
- People preparing a Hermes upgrade, migration, or post-update verification.

It is not:

- an official Hermes replacement;
- a cloud scanner;
- an auto-repair bot;
- a credentials validator;
- a support backdoor.

## Safety model

Diagnostic commands are read-only and offline:

- no config writes;
- no gateway restart;
- no gateway platform probes;
- no cron execution;
- no plugin execution;
- no MCP tool execution;
- no platform messages;
- no network probes;
- no raw `.env`, `auth.json`, cookie, session, memory, or log payloads in reports.

Repair flow is gated:

1. `full` or `post-update` collects facts.
2. `repair-plan` turns findings into approval-required actions. It does not write.
3. `fix` requires `--plan`, `--approve action-id`, and explicit `--hermes-home` for registered executors.
4. `fix --execute` can write only through registered narrow executors.

Current registered executor:

- `config.missing`: creates a minimal parseable `config.yaml` stub after writing a backup manifest. It does not configure providers, API keys, or secrets.

## Install

From source:

```bash
git clone https://github.com/AlekseiUL/hermes-system-doctor
cd hermes-system-doctor
python -m pip install -e ".[dev]"
```

After package publication, the intended one-shot path is:

```bash
uvx hermes-system-doctor --help
```

Until then, use the source install above.

## Quick start

Create a Markdown report:

```bash
hermes-system-doctor full --hermes-home ~/.hermes --markdown --output hermes-system-report.md
```

Create a JSON report for automation:

```bash
hermes-system-doctor full --hermes-home ~/.hermes --json --output report.json
```

Generate a repair plan:

```bash
hermes-system-doctor repair-plan --input report.json --output repair-plan.json
```

Preview a specific approved action:

```bash
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001 --output fix-preview.json
```

Apply only if the action is a registered executor and you accept the risk:

```bash
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001 --execute --output fix-result.json
```

## Operating flow

```mermaid
flowchart LR
    A[Hermes home] --> B[full / post-update report]
    B --> C[repair-plan]
    C --> D[fix preview]
    D --> E{registered executor?}
    E -- no --> F[blocked]
    E -- yes + --execute --> G[backup manifest + minimal change]
    G --> H[run doctor again]
```

## Current commands

```bash
hermes-system-doctor discover --hermes-home ~/.hermes --json
hermes-system-doctor quick --hermes-home ~/.hermes --markdown --output report.md
hermes-system-doctor full --hermes-home ~/.hermes --json --output report.json
hermes-system-doctor post-update --hermes-home ~/.hermes --json
hermes-system-doctor repair-plan --input report.json --output repair-plan.json
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001 --output fix-preview.json
```

`quick` runs the current safe core checks. `full` and `post-update` also include local post-update drift diagnostics.

## Example: safe config repair

If a named profile exists but lacks `config.yaml`:

```bash
hermes-system-doctor full --hermes-home ./demo-hermes --json --output report.json
hermes-system-doctor repair-plan --input report.json --output repair-plan.json
hermes-system-doctor fix --hermes-home ./demo-hermes --plan repair-plan.json --approve rp-0001 --execute --output fix-result.json
hermes-system-doctor full --hermes-home ./demo-hermes --json --output after.json
```

Expected behavior:

- backup manifest is created under the selected Hermes home;
- a minimal parseable `config.yaml` stub is created;
- no secrets or providers are added;
- a follow-up doctor scan no longer reports that `config.missing` finding.

## Requirements

- Python 3.10+
- Local Hermes Agent home, usually `~/.hermes`
- `PyYAML`

## Development gate

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
python -m build
```

The release gate also smokes the built wheel, unpacks the sdist and runs tests there, and scans tracked files plus build artifacts for private paths, bytecode, secret-like assignments, and accusation language.

## Русская версия

**Hermes Agent System Doctor** — безопасный диагностический CLI для Hermes Agent. Он не заменяет штатный `hermes doctor`, а смотрит шире: профили, gateway-сигналы, cron, logs, auth-поверхности, memory, skills, plugins, MCP и post-update drift.

Главная идея: сначала факты, потом план, потом только точечный repair под явным approval.

Что можно показать зрителям:

- сделал отчёт по локальному Hermes без чтения секретов;
- получил список рисков и `UNKNOWN`, а не фальшивый зелёный статус;
- сгенерировал repair-plan;
- применил только один разрешённый action через `fix --execute`;
- проверил повторным scan, что finding ушёл.

Безопасная граница:

- диагностические команды ничего не чинят и не перезапускают;
- `repair-plan` ничего не пишет;
- `fix --execute` пишет только через зарегистрированные узкие executors;
- сейчас зарегистрирован только `config.missing` — создание минимального `config.yaml` stub без ключей и провайдеров.

## Canonical source

This project is maintained by Aleksei Ulianov / Sprut_AI.
Original repository: https://github.com/AlekseiUL/hermes-system-doctor

If you found this project mirrored, repackaged, or redistributed elsewhere, check this repository as the source of truth.

## Attribution

Where permitted by the applicable license, if you reuse, fork, modify, package, or publish this work, keep the original copyright and license notice and link back to the canonical repository.

## License

MIT. See [LICENSE](LICENSE).
