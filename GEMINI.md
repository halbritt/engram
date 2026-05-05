# Gemini CLI Project Instructions

This file provides foundational mandates and guidance for Gemini CLI when working within the Engram codebase.

## Foundational Mandates

- **Precedence:** These instructions take absolute precedence over general workflows.
- **Core Principles:** Adhere strictly to the "Architecture Principles" and "Change Discipline" defined in [AGENTS.md](./AGENTS.md).
- **Privacy & Security:** Engram is local-first. Never introduce cloud dependencies or allow user data to leave the machine.

## Reference Documentation

For detailed project context, follow the reading order and guidelines established in [AGENTS.md](./AGENTS.md).

## Local Development Standards

- **Infrastructure:** Use only local infrastructure (Python, PostgreSQL, pgvector).
- **Tooling:** Utilize the `Makefile` targets for installation, migrations, testing, and pipeline execution.
- **Testing:** Always run `make test` or `make test-docker` to validate changes.
- **Schema:** Use `make schema-docs` to update schema documentation; do not edit manually.

## Multi-Agent & Review Process

- Follow the structured review loops and coordinator judgment patterns described in [AGENTS.md](./AGENTS.md) and the referenced process documents in `docs/process/`.
- Feedback and reviews are stored under `docs/reviews/`.
