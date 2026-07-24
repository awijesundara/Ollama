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
- PDF, DOCX, text, structured-text, source-code, and image attachments.
- Live, transient model reasoning separated from the final answer.
- Native downloadable PDF export for assistant responses.
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

## Docker (host-managed Ollama)

The Docker stack contains the Chainlit application and a local-only nginx
gateway. Ollama and its models stay on the host and are not copied into an
image or volume.

Start Ollama on the host, ensure the configured model is available, and launch
the stack:

```bash
ollama serve
ollama pull gpt-oss:20b
docker compose up --build -d
```

Open <http://localhost:8000>. The default gateway binds only to
`127.0.0.1` and supplies a single local development identity. Encrypted chat
data and generated application secrets are held in separate named volumes, so
container rebuilds do not erase them.

Choose another installed model or port with environment variables:

```bash
OLLAMA_CHAT_MODEL=llama3.2:3b APP_PORT=8080 docker compose up --build -d
```

For image understanding, configure a locally installed vision-capable Ollama
model separately:

```bash
OLLAMA_VISION_MODEL=qwen3.5:latest docker compose up --build -d
```

The upload pipeline accepts PDF, DOCX, TXT, Markdown, CSV, JSON, YAML,
HTML/XML, common source-code formats, PNG, JPEG, WebP, and GIF. Text is
extracted into the model prompt. Images are validated and sent only to the
vision model. Raw uploads are not added to the encrypted history; extracted
text and model responses are stored as conversation content. The defaults
allow 10 files of up to 10 MB each and at most 100,000 extracted characters.

When Ollama returns a `thinking` stream, the UI displays it live in a temporary
**AI is thinking** chat bubble. The bubble is removed as soon as the final
answer begins, keeping the saved conversation clean. Disable this per
deployment with `SHOW_MODEL_THINKING=false`.

Every completed assistant response includes a **Download PDF** action. Users
can also type `/pdf`, `/pdf <custom text>`, or ask naturally to convert the
latest answer into a PDF. The settings sidebar shows Ollama as the active local
provider; ChatGPT, Gemini, and Claude appear as disabled **Coming soon**
providers until their API integrations are configured.

Docker Desktop on macOS and Windows resolves `host.docker.internal`
automatically. The Compose file also provides the hostname on Linux, but the
host Ollama server must accept connections from the Docker bridge. For example,
run Ollama with `OLLAMA_HOST=0.0.0.0:11434` and restrict port 11434 with the
host firewall.

Useful lifecycle commands:

```bash
docker compose logs -f
docker compose down
docker compose down --volumes  # permanently deletes stored chats and secrets
```

Do not expose the included gateway on a network: its fixed local identity is
only suitable for a single-user machine. For a server deployment, keep the app
behind an authenticating reverse proxy that overwrites the `X-Remote-*`
headers, or configure the existing LDAPS authentication mode. Set production
secrets explicitly and use HTTPS as described in the deployment checklist.

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

Automatic extraction is enabled by default and saves durable, useful facts
rather than complete transcripts. Users retain `/memories`, `/memory-off`,
`/forget`, and export/deletion controls.

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
