# Chainlit Ollama Persistent Memory

An authenticated, multi-user Chainlit application with stateless Ollama
generation and encrypted per-user file storage for chat history, personal
memory, summaries, preferences, and audit records. PostgreSQL remains an
optional backend.

The complete product blueprint and backlog are preserved in
[`BACKLOG.md`](BACKLOG.md). The original repository was empty; its assessment
is recorded in [`ASSESSMENT.md`](ASSESSMENT.md).

## Capabilities

- Windows AD authentication over certificate-validated LDAPS, using
  `objectGUID` as the immutable ownership key.
- Trusted reverse-proxy header authentication as an alternative deployment
  mode.
- Chainlit 2.11+ ChatGPT-style web UI with searchable history, new chat,
  authenticated resume, settings sidebar, streaming, and dark/light themes.
- AES-256-GCM encrypted per-user files with opaque keyed filenames, atomic
  writes, tamper detection, and `0600` file permissions.
- Global and thread-scoped memory with server-derived ownership on every query.
- Explicit memory commands, settings, actions, JSON export, and confirmed
  destructive operations.
- Secret, credential, prompt-injection, duplicate, length, scope, and per-user
  limit checks.
- Conversation summarization and configurable recent-message context.
- Automatic structured memory extraction, disabled by default and gated by
  both administrator configuration and user preference.
- Optional Ollama embeddings and user/thread-scoped pgvector retrieval.
- Conflict detection with user-confirmed replacement.
- Audit events, JSON logging, Prometheus metrics, retention tooling, and health
  checks.
- Alembic migrations, unit/security/integration tests, and CI.

Ollama never stores memory and never receives database or LDAP credentials.

## Structure

```text
app.py                         Chainlit callback registration
src/auth/                      AD authentication and immutable identity
src/chat/                      lifecycle, history, prompts, summaries
src/database/                  encrypted-file and PostgreSQL Chainlit layers
src/memory/                    models, validation, repository, service, retrieval
src/ollama/                    native async Ollama client
src/security/                  secret detection and audit persistence
src/ui/                        settings, actions, export and confirmation
migrations/                    Chainlit, memory, audit and pgvector schemas
tests/                         unit, security and PostgreSQL integration tests
deployment/                    systemd, nginx, logrotate, backup/recovery
scripts/                       migration, health and retention entrypoints
```

## Requirements

- Python 3.11–3.13
- Chainlit 2.11+
- Ollama with the configured chat and embedding models
- Windows AD reachable through LDAPS, or an authenticating reverse proxy
- A protected local filesystem directory

PostgreSQL 15+ with `pgcrypto` and `pgvector` is needed only when
`STORAGE_BACKEND=postgresql`.

## Configuration

Copy `.env.example` to a protected environment file and replace every
placeholder. Never commit `.env`.

Production validation requires HTTPS, a Chainlit authentication secret, a
user-hash salt and—when `AUTH_MODE=ldap`—LDAPS, a base DN, and CA file.
`MEMORY_AUTO_EXTRACTION=false` is the safe default.

### Encrypted file storage

This is the default backend:

```text
STORAGE_BACKEND=encrypted_files
ENCRYPTED_STORAGE_DIR=/var/lib/chainlit-ollama-memory/users
ENCRYPTED_STORAGE_KEY=<base64-encoded 32-byte key>
```

Generate the master key once in a secure administrative environment:

```bash
openssl rand -base64 32
```

Store it only in the root-owned `0640` environment file or a secrets manager.
Losing the key makes every user file unrecoverable. Exposing it compromises
every file, so back it up separately from the encrypted data.

Each user sees their exact opaque `.enc` path in the Chainlit welcome message
and through **Where is my data?**. The path does not contain their username,
UPN, or AD GUID.

### AD mode

Set `AUTH_MODE=ldap`. The user password is used only for the in-memory LDAPS
bind and is never stored or logged. The search must return exactly one entry
with `objectGUID`.

### Trusted proxy mode

Set `AUTH_MODE=header`. Only use this when Chainlit listens on loopback or a
private socket and the proxy overwrites the configured identity headers.
Never expose the Chainlit port directly to clients.

## Installation

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Optional PostgreSQL backend

Set `STORAGE_BACKEND=postgresql`, configure `DATABASE_URL`, and apply:

Use a migration role rather than the runtime application role:

```bash
alembic -x database_url="$DATABASE_URL" upgrade head
```

The migrations create the Chainlit 2.11 SQLAlchemy schema, custom memory
tables, preferences, summaries, audit events, and a 768-dimensional vector
column for `embeddinggemma`. If the configured embedding model has a different
dimension, add a migration before enabling vector search.

## Run

```bash
chainlit run app.py --host 127.0.0.1 --port 8000
```

The reverse proxy is responsible for public TLS and WebSocket forwarding.

## Memory commands

```text
/remember <text>
/remember-global <text>
/remember-chat <text>
/memories
/forget <short-id>
/forget-all-global
/forget-all-chat
/memory-on
/memory-off
/auto-memory-on
/auto-memory-off
```

Automatic extraction requires both `MEMORY_AUTO_EXTRACTION=true` and the
user’s automatic-memory preference.

## Verification

```bash
ruff format --check .
ruff check .
mypy src
pytest
```

PostgreSQL-backend tests require a migrated disposable database in
`TEST_DATABASE_URL`. CI provisions pgvector PostgreSQL, tests migrations in
both directions, and runs the full suite.

## Health and retention

```bash
python scripts/health_check.py
python scripts/retention.py
```

Schedule retention with a systemd timer or equivalent. Health output contains
only booleans and never connection details.

## Deployment checklist

1. Back up the encrypted user directory and encryption key separately, then
   test an isolated restore.
2. Install into a versioned directory under `/opt/chainlit-ollama-memory`.
3. Store environment values in a root-owned `0640` file.
4. Validate AD certificate trust and immutable `objectGUID` mapping.
5. If using PostgreSQL, apply migrations with a separate migration role.
6. Confirm both required Ollama models using the health check.
7. Install the nginx, systemd, and logrotate examples.
8. Run the complete CI suite against the release.
9. Validate Alice/Bob isolation, restart persistence, and thread resume.
10. Promote traffic and monitor audit, error, latency, and pool metrics.

## Rollback checklist

1. Drain traffic and stop the service.
2. Preserve logs and take a verified storage backup.
3. Point `current` to the previous versioned release.
4. Do not downgrade migrations unless the previous release is incompatible
   with additive tables.
5. Treat the `0001` and `0003` downgrades as destructive because they delete
   memory and chat history.
6. Restart, run health checks, and verify authentication and thread resume.

See [`deployment/BACKUP_AND_RECOVERY.md`](deployment/BACKUP_AND_RECOVERY.md)
for the backup and recovery procedure.
