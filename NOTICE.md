# NOTICE

Hermes Agent System Doctor is maintained by Aleksei Ulianov / Sprut_AI.

Canonical source: https://github.com/AlekseiUL/hermes-system-doctor

This is an independent companion tool for Hermes Agent installations. It is not an official Nous Research / Hermes Agent component unless explicitly accepted upstream.

The project is designed around a safety-first flow:

1. diagnostic commands collect redacted local facts without service restarts, external calls, cron runs, plugin execution, MCP execution, or raw secret dumps;
2. `repair-plan` generates approval-required actions without writing;
3. `fix --execute` can write only through registered, narrow, tested executors under an explicit `--hermes-home`.

Current registered mutating executor: `config.missing`, which creates a minimal parseable `config.yaml` stub after writing a backup manifest. It does not add credentials, providers, OAuth tokens, or model settings.

Copyright (c) 2026 Aleksei Ulianov / Sprut_AI
