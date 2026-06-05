# Security Policy

## Reporting

Please report security-sensitive findings privately through the canonical repository owner contact channels rather than posting secrets or raw logs in public issues.

## Safety model

Hermes Agent System Doctor is designed to be read-only by default.

Default mode must not:

- edit configuration;
- restart services;
- run cron jobs;
- send messages through gateways;
- call external APIs;
- print API keys, OAuth tokens, cookies, chat IDs, `.env` values, `auth.json` payloads, or raw session contents.

Reports should show presence, category, status, and redacted evidence only.
