# Security Policy

## Reporting

Please report security-sensitive findings privately through the canonical repository owner contact channels. Do not post real `.env`, `auth.json`, cookies, access tokens, chat IDs, private logs, memory files, or session payloads in public issues.

Canonical source: https://github.com/AlekseiUL/hermes-system-doctor

## Safety model

Hermes Agent System Doctor separates diagnostics from repair.

Diagnostic modes are designed to be read-only and offline:

- no config writes;
- no gateway restart;
- no gateway platform probes;
- no cron execution;
- no plugin execution;
- no MCP tool execution;
- no platform messages;
- no network probes;
- no raw `.env`, `auth.json`, cookie, session, memory, or log payloads in reports.

`repair-plan` is dry-run only. It turns findings into approval-required actions, but performs no writes.

`fix --execute` can write only through registered narrow executors. Each executor must have tests for approval, backup, diff/rollback intent, no symlink/path escape, no overwrite, and a follow-up doctor scan proving the finding was resolved.

Currently registered mutating executor:

- `config.missing`: writes a backup manifest and creates a minimal parseable `config.yaml` stub. It does not add providers, API keys, OAuth tokens, model settings, or secrets.

## Data handling

Reports should show presence, category, status, safe labels, and redacted evidence only.

Do not submit real secrets when reporting bugs. If a report is needed, reproduce with a synthetic Hermes home or redact sensitive files first.

## Not a credential validator

This tool inventories auth/secret-adjacent surfaces by presence and shape. It does not verify whether credentials work, log into providers, call external APIs, or test gateway delivery.
