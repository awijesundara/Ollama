# Encrypted per-user storage

## What is stored

Each authenticated user has one encrypted JSON document containing:

- the stable Chainlit user record;
- chat threads, messages, feedback, and element metadata;
- global and thread memories;
- memory preferences;
- thread summaries;
- memory audit events;
- optional memory embeddings.

Credentials and detected secrets are redacted before the history layer writes
them. Uploaded binary files are disabled by default.

## Where it is stored

`ENCRYPTED_STORAGE_DIR` controls the root directory. The default production
location is:

```text
/var/lib/chainlit-ollama-memory/users
```

Each filename is an HMAC-SHA-256 keyed hash of the authenticated immutable
identifier (the AD object GUID in LDAP mode):

```text
<64-character opaque value>.enc
```

The username, UPN, display name, and AD GUID do not appear in the filename.
The authenticated user can see their exact path from the Chainlit welcome
message or **Where is my data?**.

## Cryptography

- AES-256-GCM authenticated encryption.
- Random 96-bit nonce for every write.
- Per-user file key derived from the 256-bit master key and opaque file ID.
- File identity/version bound as authenticated associated data.
- Modified ciphertext fails authentication instead of returning corrupted
  history.
- Atomic temporary-file write, `fsync`, and rename.
- POSIX advisory lock serializes updates to one user envelope.
- Directory mode `0700`; file and lock mode `0600`.

## Master key

Generate once:

```bash
openssl rand -base64 32
```

Set the result as `ENCRYPTED_STORAGE_KEY`. Do not commit it or store it beside
the encrypted user directory.

- If the key is lost, the files cannot be recovered.
- If the key and encrypted directory are stolen together, all user data is
  compromised.
- Back up the key in a separately controlled secrets manager.
- Restore tests must prove both ciphertext integrity and authenticated thread
  resume.

## Multi-host limitation

The encrypted-file backend is intended for one Chainlit host with local or
single-writer shared storage. For multiple active application hosts, use
PostgreSQL or a storage service with distributed transactions and locking.
