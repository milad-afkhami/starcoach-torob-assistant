# Plan B before you leave

A Persian in-person shopping assistant built for the Torob Starcoach2026 challenge. Choose an exact product, lock your budget/location/visit requirements, and keep an independent nearby seller ready. When a seller is unavailable or changes terms, confirm the reply and inspect the revised plan without repeating your requirements.

**Current state:** local implementation and verification are tracked in [kanban](docs/insured-vibe-coding/kanban.md). Public deployment and final submission are not yet complete. [Architecture](docs/architecture.md), [measured recovery results](results/recovery.json), [QA evidence](docs/qa-evidence/) and [implementation decisions](docs/implementation-progress.md) distinguish verified behavior from pending gates.

## Run locally

Requires Python3.12, uv, Node24/npm and the organizer's supplied `torob-dataset.zip`. Docker and a locally authenticated Codex CLI are needed only for actual AI calls. Direct search, planning and confirmed-reply recovery work without the worker.

```bash
uv sync --locked
npm --prefix frontend ci
PYTHONPATH=backend uv run python scripts/build_catalogue.py --archive /absolute/path/to/torob-dataset.zip
npm --prefix frontend run build
cp .env.example .env
chmod 600 .env
```

Edit `.env`: generate separate random256-bit `SESSION_SECRET` and `MODEL_WORKER_TOKEN` values, set PUBLIC_ORIGIN to `http://127.0.0.1:8651`, and retain the catalogue/state paths. Do not put credentials in Git, commands, browser configuration or images. The example's placeholder secrets must be replaced before use. Then start the actual app:

```bash
uv run --env-file .env python scripts/dev_server.py
```

Open `http://127.0.0.1:8651`. The labelled sample scenario uses a fixed historical test visit and simulated replies. To enable AI, configure the isolated local worker as described in [model-runtime.md](docs/model-runtime.md), with MODEL_WORKER_BASE_URL matching this app and MODEL_WORKER_LOOPBACK_TEST=1 for this local HTTP test. Production uses HTTPS and no loopback exception.

The importer accepts root-level or nested CSV layouts and validates the known payload hashes. It preserves the entire6476-shop/225903-product/331506-offer dataset. A changed CSV requires inspection and an explicit new accepted hash; the importer does not silently accept unrelated data. The archive and generated catalogue are not distributed through this public source repository; obtain them through the organizer's challenge resource. They are never exposed as web assets.

## Verify

```bash
uv run pytest -q
uv run ruff check backend tests scripts
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
PYTHONPATH=backend uv run python scripts/evaluate_recovery.py
```

Browser tests require the running actual app and Chrome. Unit tests do not replace the separately recorded real Codex/UI acceptance. The known upstream Starlette/httpx TestClient deprecation warning is recorded; it has not caused a runtime failure. Do not reset the shared model quota to rerun tests.

## Deploy

See [deployment.md](docs/deployment.md) for the private image, persistent state, measured resource use, source-upload allowlist and concrete Liara proposal. The application contains no Codex authentication. A local outbound worker supplies model access; its absence is shown honestly while deterministic shopping remains available. The image includes the private catalogue and must not be published to a public registry.

## Evidence, not invented certainty

Recorded prices/hours are historical, stock is unknown, all supplied phone numbers are synthetic and most shop names are anonymized. Source, user-reported and simulated information remain distinct. Follow-up generates a draft; the app never contacts a seller. Torob/TorobPay/navigation links are user-clicked handoffs, not live stock/credit/ride integrations. [Contact limitations](docs/contact-limitations.md) explains the boundary.

Money stays an exact decimal string across the API and uses BigInt formatting in the browser. Unknown or flagged prices cannot win automatic ranking. Recovery cannot silently change a product, budget, radius, visit time or payment requirement. No-response sellers remain recheckable without being promoted as confirmed available.

## Attribution

Mandatory data and challenge supplied by Torob/Starcoach. Locally bundled Vazirmatn is distributed under its included OFL1.1 license in `frontend/public/fonts/OFL.txt`. Third-party package versions are locked in `uv.lock`, `requirements.lock` and `frontend/package-lock.json`.
