# Enigma

A minimal self-hosted todo list. Python standard library only — no pip
installs, no build step, one file.

## Features

- Session sign-in
- Add and remove todos
- Docker socket integration for container awareness
- `/health` endpoint wired into the compose healthcheck

## Run

```bash
docker compose up
```

Enigma requires a free license key for persistent storage: register at
https://requests.cici.lt/enigma-setup, then set `ENIGMA_LICENSE_KEY` in
the compose file. Without a key it runs in evaluation mode (in-memory
storage) and `/health` reports `unlicensed` — see `DEBUGGING.md`.
