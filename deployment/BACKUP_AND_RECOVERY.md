# Backup and recovery

Use a dedicated backup account and encrypted destination. Never place database
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

