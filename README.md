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
