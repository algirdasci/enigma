# Enigma

A minimal self-hosted todo list. Python standard library only — no pip
installs, no build step, one file.

## Features

- Session sign-in
- Add and remove todos
- `/health` endpoint wired into the compose healthcheck

## Run

```bash
docker compose up
```

Enigma expects a Postgres-compatible host from `DATABASE_URL`. Without
one it starts in degraded mode (in-memory storage) and `/health` reports
unhealthy — see `DEBUGGING.md`.
