# Existing Application Assessment

Assessment date: 2026-07-23

## Current state

The repository is a new, empty Git repository on the `main` branch. It contains
no application code or commits, so there is no existing behavior to reproduce
or configuration to back up.

| Area | Finding |
| --- | --- |
| Project structure | No application files |
| Chainlit version | Not installed or declared |
| Python version | Not declared |
| Authentication | No LDAP/AD implementation |
| AD identity field | Not defined |
| Ollama client | Not implemented |
| Persistence | PostgreSQL and Chainlit persistence not implemented |
| Reverse proxy | Not configured |
| Deployment | No systemd or deployment files |

## Compatibility risks

- Chainlit lifecycle and data-layer APIs vary by release. Runtime integration
  must be verified against the pinned version before deployment.
- The AD provider and immutable identifier format are organization-specific.
  Authentication cannot be completed without the directory connection details;
  ownership code will require a non-empty immutable identifier.
- PostgreSQL integration tests require an available test database.
- The target Ollama model and server must be checked during deployment.

## Implementation approach

This is a greenfield implementation. The first tranche adds:

- typed environment configuration;
- identity and memory domain models;
- centralized secret and memory validation;
- PostgreSQL migrations and an ownership-scoped repository;
- a Chainlit-independent memory service;
- explicit memory-command parsing;
- safe prompt construction;
- unit and security tests.

Runtime Chainlit, AD, and Ollama adapters will be kept thin and added only
after their concrete versions and deployment settings are known.

## Files planned

- `BACKLOG.md` — source implementation blueprint.
- `app.py` and `src/` — modular application.
- `migrations/` — Alembic migrations.
- `tests/` — unit, security, and PostgreSQL integration tests.
- `deployment/` and `README.md` — deployment and rollback guidance.

