# Implementation status

Source implementation completed on 2026-07-23. Runtime verification was not
performed because the repository owner explicitly requested that nothing be
run on the local computer.

## Epic coverage

| Epic | Implementation |
| --- | --- |
| 0 Assessment | `ASSESSMENT.md`, feature branch, `.gitignore`, rollback docs |
| 1 Structure/config | Modular `src/`, typed settings, constrained dependencies |
| 2 History | Encrypted-file and PostgreSQL data layers, resume rebuild |
| 3 Identity | AD `objectGUID`, trusted proxy mode, server-session identity |
| 4 Explicit memory | Repository, validator, commands, prompt injection |
| 5 Preferences/UI | Persistent settings, actions, confirmation, JSON export |
| 6 Summaries | Owned summaries, threshold updates, context budgeting |
| 7 Extraction | JSON schema, policy gates, conflict workflow, default-off gate |
| 8 Semantic search | pgvector migration, Ollama embeddings, scoped scoring |
| 9 Operations | JSON logs, metrics, health, systemd, nginx, backup/recovery |

The default backend is now `encrypted_files`: one AES-256-GCM envelope per
authenticated user. PostgreSQL remains available through
`STORAGE_BACKEND=postgresql`.

## Security invariants implemented

- Browser payloads never supply ownership identifiers.
- All custom memory reads and mutations include the authenticated identifier.
- Thread resume checks the Chainlit data-layer author before rebuilding state.
- Shared thread viewing is disabled and denied.
- Secret-bearing messages are redacted by the persistence layer and withheld
  from Ollama.
- Stored memory is XML-escaped, delimited, and described as untrusted data.
- Automatic memory is gated by administrator and user settings.
- Destructive UI operations require confirmation.
- Audit reasons contain categories, not rejected secret values.
- Header authentication requires an authenticating proxy and private Chainlit
  listener.

## Verification assets

- Unit tests for configuration, identity, commands, history, extraction,
  normalization, secret rejection, prompt construction, and budgeting.
- Security tests for cross-user access and prompt injection.
- PostgreSQL integration tests for global/thread isolation, delete isolation,
  concurrent duplicates, and rollback.
- CI with pgvector PostgreSQL, formatting, linting, strict typing, tests, and
  migration downgrade/upgrade.
- Load harness and scenario matrix.

## Required environment validation

Before production deployment, operators must:

1. Run CI against the release.
2. Confirm the configured AD filter returns exactly one `objectGUID`.
3. Confirm the embedding model produces 768 dimensions or add a matching
   migration.
4. Run the Alice/Bob restart and isolation scenario.
5. Validate systemd hardening and nginx trusted-header behavior.
6. Perform and document a PostgreSQL restore test.

## Intentionally out of scope

The blueprint explicitly excludes unrestricted model filesystem or SQL access,
shared/team memory, full document RAG, fine-tuning, credential storage, and
Kubernetes. None of these were added.
