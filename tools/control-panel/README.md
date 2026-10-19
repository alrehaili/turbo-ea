# Control panel

A desktop window (Java Swing, no dependencies) for running Turbo EA during local
development without Docker. Run `panel.cmd` on Windows or `./panel.sh` on macOS/Linux
from the repository root. Each launch compiles `ControlPanel.java` into
`.runtime/classes` (a second or two), then opens the window.

The window has one side for the backend and one for the frontend. Each side gives you:

- a live log, coloured by level, with a filter, an *Errors & warnings* switch, *Follow*,
  copy and clear;
- start, stop, restart and *Open in browser*;
- the port, editable while the app is stopped (press Enter to apply);
- **Keep running**: if the app exits on its own, the panel restarts it after 2 s, 4 s,
  8 s… up to 30 s. It gives up after six crashes in a row, and the count resets once
  the app has stayed up for a minute;
- backend only: **Auto-reload** (`uvicorn --reload`), on by default.

*Settings…*, *Start both* and *Stop both* are at the top. Closing the window stops both
apps, after asking. Only one panel can be open at a time.

## What it runs

| App | Command | Notes |
|---|---|---|
| Backend | `backend/.venv/…/python -m uvicorn app.main:app --host 127.0.0.1 --port <port> [--reload]` in `backend/` | Creates `backend/.venv` and runs `pip install -e ".[dev]"` on first start. Checks PostgreSQL is reachable before starting. |
| Frontend | `node node_modules/vite/bin/vite.js --port <port> --strictPort` in `frontend/` | Runs `npm install` first when Vite is missing. Proxies `/api` to the backend port set in the panel (`TURBO_EA_API_TARGET`, read by `vite.config.ts`). |

The first user to register becomes admin. API docs are at `/api/docs` while
`ENVIRONMENT=development`.

## Settings (backend/.env)

The backend reads its configuration with `os.getenv` only, so the panel loads
`backend/.env` and passes every `KEY=value` line to uvicorn as an environment variable.
*Settings…* edits that file:

- **Common**: database connection, startup seeds (`SEED_DEMO`, `SEED_BPM`, `SEED_PPM`,
  `SEED_SECURITY`, `SEED_NORA`, `RESET_DB`), environment, secret key, CORS, AI and SMTP.
- **Raw .env**: the whole file, for any other variable.

Existing lines are rewritten in place, so comments and order survive. Settings apply on
the next backend start; saving while it runs offers a restart.

`RESET_DB=true` drops every table on start. The panel asks before each such start and
never restarts the backend automatically while it is on.

## Ports and other apps

Before it starts an app, the panel checks the port. If something else is listening there,
the app is not started, and the panel names the process and its PID.

The panel stops only processes it started itself, plus one more case: a leftover
Turbo EA process from an earlier run, which it offers to stop with *Stop it*. It
recognises one by its command line, which must contain this checkout's folder or
`app.main:app`. Other apps on the same port are never touched.

## Local files

`settings.local.properties` (ports, keep-running, auto-reload) and `.runtime/` (compiled
classes, the single-instance lock) are written next to the source and are git-ignored,
as is `backend/.env`.
