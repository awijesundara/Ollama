# Backup and recovery

## Encrypted file backend

Back up `/var/lib/chainlit-ollama-memory/users` as ordinary binary files. The
files are already encrypted and authenticated, but the backup destination
should still be encrypted and access-controlled.

Back up `ENCRYPTED_STORAGE_KEY` separately in an organizational secrets
manager. Never store the key beside the encrypted files. A usable recovery
requires both, while theft of both compromises all user data.

Restore into an isolated directory, set mode `0700` on the directory and `0600`
on files, supply the recovered key, and use the health check plus an
authenticated thread-resume test.

## PostgreSQL backend

Use a dedicated backup account and encrypted destination. Never place
credentials on the command line; provide them through a root-readable
environment or `.pgpass`.

## Backup

```bash
pg_dump --format=custom --file=/encrypted-backups/chainlit-$(date +%F).dump chainlit
pg_restore --list /encrypted-backups/chainlit-$(date +%F).dump >/dev/null
```

Retain daily backups for 14 days, weekly backups for 8 weeks, and monthly
backups according to organizational policy. Replicate backups to a separately
controlled encrypted location.

## Restore test

Restore into an isolated database, never over production:

```bash
createdb chainlit_restore_test
pg_restore --clean --if-exists --no-owner --dbname=chainlit_restore_test backup.dump
```

Run migration status, ownership-isolation tests, thread-resume tests, and record
counts. Destroy the isolated database only after evidence is retained.

## Recovery

1. Drain Chainlit traffic.
2. Preserve the failed database and application logs.
3. Provision a replacement PostgreSQL instance.
4. Restore the most recent verified backup.
5. Apply only migrations newer than the backup.
6. use `scripts/health_check.py`.
7. Validate Alice/Bob isolation and thread resume.
8. Restore traffic and monitor error/audit rates.
