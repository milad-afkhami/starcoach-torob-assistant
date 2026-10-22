# Getting started

[← Documentation](README.md) · [Next: user guide →](user-guide.md)

Run the source locally with the organizer's catalogue. The deterministic search and recovery flow can run without AI; the optional worker enables genuine Codex assistance.

## Prerequisites

| Requirement | Purpose |
|---|---|
| Python 3.12 and uv | Locked backend environment |
| Node 24 and npm | Frontend installation, build and exact-value tests |
| Organizer's `torob-dataset.zip` | Mandatory complete catalogue; not included in Git |
| Docker and an authenticated local Codex CLI | Optional isolated model execution |
| Chrome | Optional rendered browser regression checks |

All commands below run from the repository root. These instructions create local files; they do not provision cloud resources.

## 1. Install and build

```bash
uv sync --locked
npm --prefix frontend ci
PYTHONPATH=backend uv run python scripts/build_catalogue.py --archive /absolute/path/to/torob-dataset.zip
npm --prefix frontend run build
```

The importer accepts root-level or nested CSV layouts, ignores archive metadata, and validates the accepted CSV payload hashes. It retains the complete catalogue. A genuinely different payload requires inspection and a deliberate accepted-hash update; bypassing validation is not a normal setup step.

## 2. Create private configuration

For a new checkout only:

```bash
cp .env.example .env
chmod 600 .env
```

Generate two separate random secrets locally. Running the following command twice produces independent values; put them into the private file, not into source or a screenshot:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

| Setting | Local value |
|---|---|
| `SESSION_SECRET` | First generated secret |
| `MODEL_WORKER_TOKEN` | Second generated secret, at least 32 characters |
| `PUBLIC_ORIGIN` | `http://127.0.0.1:8651` |
| `CATALOGUE_DB_PATH` | `data/catalogue.sqlite` |
| `STATE_DB_PATH` | `data/development.sqlite` |
| `PYTHONPATH` | `backend` |

The application requires its session and worker secrets even when the worker is offline. Leave the worker stopped until its optional model paths are configured. [All settings](reference.md#configuration).

> [!IMPORTANT]
> Do not overwrite an existing `.env`, catalogue or state database just to repeat this guide. Existing sessions and confirmed observations belong to that state database.

## 3. Start the application

```bash
uv run --env-file .env python scripts/dev_server.py
```

Open **http://127.0.0.1:8651**. Keep this terminal running. `/healthz` is process liveness; `/readyz` checks catalogue availability. On a fresh browser, click **دیدن سناریوی نمونه** to load the repeatable source-row simulation.

## 4. Enable AI, optionally

Configure the local static Codex executable, its authentication file, the pinned trusted runtime image, and the matching worker URL/token using [model-runtime.md](model-runtime.md). For this loopback setup, set `MODEL_WORKER_BASE_URL=http://127.0.0.1:8651` and `MODEL_WORKER_LOOPBACK_TEST=1`. Public HTTP origins are not supported.

Start a second terminal:

```bash
uv run --env-file .env python scripts/model_worker.py
```

The interface should show **دستیار آماده** after a heartbeat. The model subprocess has only its dedicated model authentication and request/result mounts, not the application database or worker token. Personal model authentication remains local.

## 5. Exercise the product

Follow [the user guide](user-guide.md#practice-the-complete-recovery). Confirm an unavailable seller, inspect the fallback promotion and price delta, then open the updated destination. No seller is contacted.

## Verification commands

```bash
uv run pytest -q
uv run ruff check backend tests scripts
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
PYTHONPATH=backend uv run python scripts/evaluate_recovery.py
```

The browser suite needs the actual app and Chrome. The recovery evaluator uses its documented fixtures/catalogue requirements; it does not contact sellers. Actual model evaluations consume the persistent shared model budget. See [evaluation](evaluation.md) before interpreting the outputs.

## Stop and restart

Stop the app or worker with <kbd>Ctrl</kbd> + <kbd>C</kbd> in its terminal. Restart using the same private configuration and state path. Sessions persist in SQLite; model availability expires when heartbeats stop. Search/manual recovery remain available while the worker is offline.

For container packaging, persistent mounts and HTTPS hosting, continue with [deployment](deployment.md). For a failed startup or unavailable worker, use [troubleshooting](reference.md#troubleshooting).
