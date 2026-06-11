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

## Repair executor safety contract

`fix --execute` is intentionally narrower than diagnostics. A repair is allowed only when all of the following are true:

- the finding maps to an explicitly registered executor ID;
- the operator supplied the required approval for the specific action;
- the target path is inside the selected Hermes home/profile scope;
- the target path is not a symlink and cannot escape through `..`, absolute-path tricks, or resolved-path mismatch;
- the executor can produce a backup/manifest or an explicit no-op reason before mutation;
- the executor can show the intended diff/rollback information without exposing secrets;
- the executor has tests for approval handling, backup/rollback intent, path-safety failures, refusal to overwrite unsafe existing content, and a follow-up doctor scan proving the finding is resolved.

Forbidden repair behavior:

- reading, printing, copying, templating, or writing real API keys, OAuth tokens, cookies, chat IDs, memory payloads, session data, or raw logs;
- adding providers, model credentials, webhook URLs, gateway tokens, or platform delivery settings;
- restarting gateways, executing cron jobs, invoking plugins, running MCP tools, sending platform messages, or making network probes;
- following symlinks, writing outside the selected Hermes home, deleting user data, or modifying files that are unrelated to the finding being repaired;
- silently overwriting non-empty existing config without an operator-visible backup and diff.

Currently registered mutating executor:

- `config.missing`: writes a backup manifest and creates a minimal parseable `config.yaml` stub. It does not add providers, API keys, OAuth tokens, model settings, gateway settings, platform settings, webhook URLs, or other secrets.

## Data handling

Reports should show presence, category, status, safe labels, and redacted evidence only.

Do not submit real secrets when reporting bugs. If a report is needed, reproduce with a synthetic Hermes home or redact sensitive files first.

## Not a credential validator

This tool inventories auth/secret-adjacent surfaces by presence and shape. It does not verify whether credentials work, log into providers, call external APIs, or test gateway delivery.
