# Chainlit Ollama Memory

Multi-user persistent chat history and personal memory for an authenticated
Chainlit application backed by PostgreSQL and Ollama.

The repository is being built from the implementation plan in
[`BACKLOG.md`](BACKLOG.md). The current tranche establishes the Phase 1
security and persistence foundation. Chainlit lifecycle, AD authentication,
thread-history persistence, and Ollama streaming adapters are not wired yet.

## Requirements

- Python 3.11–3.13
- PostgreSQL 15+ with permission to enable `pgcrypto`
- A supported Chainlit release (to be selected and pinned when its current API
  can be validated)
- Ollama and the configured chat model

## Development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
mypy src
```

Copy `.env.example` to `.env` and replace placeholder values. Never commit
`.env`. Production configuration fails validation unless HTTPS and LDAPS are
used and required authentication values exist.

## Database migration

Use a deployment role that can create tables and enable `pgcrypto`:

```bash
alembic -x database_url="$DATABASE_URL" upgrade head
```

Before production use, `migrations/env.py` will be updated to read the database
URL from the validated runtime/deployment environment rather than
`alembic.ini`. The checked-in URL is intentionally unusable.

## Deployment checklist

1. Back up PostgreSQL and test a restore.
2. Create a least-privilege application role and separate migration role.
3. Install the application into a versioned release directory.
4. Create a root-owned environment file with mode `0640`.
5. Verify LDAPS certificate validation and immutable AD identifier mapping.
6. Apply migrations using the migration role.
7. Check PostgreSQL, Ollama, and required model health.
8. Start the service as a non-root account.
9. Run the Alice/Bob isolation integration scenario in `BACKLOG.md`.
10. Promote traffic only after thread resume and restart persistence pass.

## Rollback checklist

1. Stop or drain the application.
2. Preserve logs and take a database backup.
3. Point the service to the previous versioned application directory.
4. Revert database migrations only when the previous application cannot
   tolerate the additive tables. The `0001` downgrade deletes memory data, so
   take and verify a backup first.
5. Restart and verify authentication, chat history, and Ollama health.

## Current limitations

- The repository began empty; no prior AD or Chainlit integration exists.
- PostgreSQL integration tests require a disposable database and are pending.
- Automatic memory extraction and semantic search are deliberately out of
  scope for Phase 1.

# Ollama
