# Rocky Linux deployment

## Accounts and paths

```text
/opt/chainlit-ollama-memory
  owner root, group chainlit
  release code read-only to chainlit

/etc/chainlit-ollama-memory/app.env
  owner root, group chainlit, mode 0640

/var/log/chainlit-ollama-memory
  owner chainlit, group chainlit, mode 0750
```

Create a versioned release directory and a `current` symlink. Build the virtual
environment once under `/opt/chainlit-ollama-memory/venv`; the service account
only needs read/execute access.

## Database privileges

The migration role needs schema DDL and extension creation. The runtime role
needs CRUD only on Chainlit and application tables plus sequence usage. Do not
grant superuser, database creation, role creation, or extension creation to the
runtime role.

## systemd hardening review

- `ProtectSystem=strict` is compatible because code and the virtual
  environment are read-only.
- `ProtectHome=true` is compatible because all runtime paths are under `/opt`,
  `/etc`, and `/var/log`.
- `PrivateTmp=true` gives the process an isolated temporary directory.
- `ReadWritePaths` permits only the application log directory.
- `RestrictAddressFamilies` retains Unix sockets, IPv4, and IPv6 for
  PostgreSQL, LDAP, and Ollama.
- `MemoryDenyWriteExecute=true` is compatible with CPython and these
  dependencies; remove only if a future native dependency demonstrably needs
  runtime code generation.

## Rollout

1. Validate configuration in a staging environment.
2. Back up and migrate PostgreSQL.
3. Switch the `current` symlink atomically to the new release.
4. Reload systemd and restart the service.
5. Run health and isolation checks through nginx.
6. Monitor failures before expanding traffic.

No systemd option should be relaxed without documenting the exact blocked path
or syscall and the narrower alternative considered.

