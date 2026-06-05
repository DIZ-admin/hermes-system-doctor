# Release Notes

## v0.1.0 — Safety-first preview

Hermes Agent System Doctor is a discovery-first companion CLI for Hermes Agent installations.

### Included

- Hermes home and profile discovery.
- Config parseability checks.
- Gateway config/log/PID signals without restart or platform probes.
- Cron metadata checks without job execution.
- Log category diagnostics without raw log excerpts.
- Auth-surface inventory without reading secret payloads.
- Memory, skills, plugins, and MCP surface diagnostics without dumping private content or executing code/tools.
- Local post-update drift signals without network fetch.
- JSON and Markdown reports.
- Dry-run `repair-plan` mode.
- Approval-gated `fix` mode with one registered executor: `config.missing` creates a minimal parseable `config.yaml` stub after writing a backup manifest.
- Safety regression tests for symlink escapes, path containment, no overwrite, failed-write cleanup, untrusted plan-field leaks, and doctor-before/after verification.

### Boundaries

- Not an official Hermes Agent component.
- Not a credentials validator.
- Not a broad autofix tool.
- Diagnostic commands are read-only and offline.
- `repair-plan` never writes.
- `fix --execute` writes only through registered narrow executors under an explicit `--hermes-home`.

### Canonical source

This project is maintained by Aleksei Ulianov / Sprut_AI.
Original repository: https://github.com/AlekseiUL/hermes-system-doctor

### Attribution

Where permitted by the applicable license, if you reuse, fork, modify, package, or publish this work, keep the original copyright and license notice and link back to the canonical repository.
