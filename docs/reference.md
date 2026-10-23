# Configuration and API reference

[← Documentation](README.md) · [Architecture](architecture.md)

## Configuration

Values belong in a private environment file. `.env.example` contains placeholders; it is not ready-to-use authentication.

| Variable | Used by | Meaning |
|---|---|---|
| `PYTHONPATH` | Local Python commands | `backend` |
| `PUBLIC_ORIGIN` | App | Exact browser origin; local helper uses `http://127.0.0.1:8651` |
| `SESSION_SECRET` | App | Independent random signing secret |
| `MODEL_WORKER_TOKEN` | App and worker | Separate random bearer secret, at least 32 characters |
| `CATALOGUE_DB_PATH` | App | Validated read-only catalogue path |
| `STATE_DB_PATH` | App | Persistent private mission/job database |
| `MODEL_WORKER_BASE_URL` | Worker | Exact app URL; HTTPS except explicit loopback tests |
| `MODEL_WORKER_LOOPBACK_TEST` | Worker | `1` only for local HTTP testing |
| `CODEX_BINARY_PATH` | Worker | Static CLI executable, not its Node launcher |
| `CODEX_AUTH_FILE` | Worker | Local model authentication file |
| `CODEX_IMAGE` | Worker | Trusted pinned runtime image; see [model runtime](model-runtime.md) |
| `MODEL_ID` | Worker | Explicit model ID; recorded build uses `gpt-6.1-sol` |

The development helper, Compose deployment and hosted app can use different ports/origins. Use the exact origin of the environment you are operating; do not reuse a production signing secret in a demo.

## HTTP route map

The running application's `/openapi.json` supplies exact request/response schemas. Interactive `/docs` and `/redoc` are disabled. This table is a navigation reference, not a replacement for schema validation.

| Method | Route | Purpose |
|---|---|---|
| GET | `/healthz`, `/readyz`, `/api/capabilities` | Liveness, catalogue readiness and model capability |
| POST | `/api/sessions` | Establish a signed browser session |
| POST | `/api/search` | Retrieve source-backed products and explicit category/budget diagnostics on no match |
| GET | `/api/locations?q=…` | Up to eight matching actual catalogue addresses/coordinates; no geocoding |
| POST | `/api/products/compare` | Exactly two source products, same-condition local feasibility and exclusion reasons |
| GET | `/api/products/{product_id}` | Exact product facts |
| GET | `/api/products/{product_id}/offers` | Offers under query constraints |
| POST | `/api/missions` | Create a selected-product mission |
| GET / PATCH | `/api/missions/{mission_id}` | Read or explicitly update an owned mission |
| GET | `/api/missions/{mission_id}/plan` | Current eligible plan |
| GET | `/api/missions/{mission_id}/history` | Recorded plan deltas |
| GET | `/api/missions/{mission_id}/actions` | Current user-clicked handoffs |
| POST | `/api/missions/{mission_id}/followups` | Prepare a targeted inquiry |
| POST | `/api/missions/{mission_id}/observations/preview` | Store a preview without applying it |
| POST | `/api/missions/{mission_id}/observations/{observation_id}/confirm` | Confirm against the expected mission revision |
| POST | `/api/missions/{mission_id}/reset` | Reset an owning simulation's observations |
| POST | `/api/turns` | Start a bounded AI turn |
| GET | `/api/turns/{turn_id}` | Poll the owned result |
| POST | `/api/turns/{turn_id}/cancel` | Cancel that turn |

Private session routes check ownership. State-changing routes require the configured Origin. IDs belonging to another session do not grant access.

<details>
<summary><strong>Private worker routes</strong></summary>

All use a worker bearer token under `/internal/model-worker`, never the browser's session cookie.

| Method | Suffix | Purpose |
|---|---|---|
| POST | `/heartbeat` | Advertise availability |
| POST | `/claim` | Atomically lease one job |
| GET | `/jobs/{job_id}` | Check the matching worker's job |
| POST | `/jobs/{job_id}/complete` | Return validated output for an exact lease/token |
| POST | `/jobs/{job_id}/fail` | Record a bounded failure |

Lease, completion-token, expiry and mission-revision checks reject late or replayed output. [Full runtime contract](model-runtime.md).

</details>

`SearchConstraints.origin_label` is an optional, at-most300-character display label; coordinates remain authoritative for geometry. It defaults to null for old missions. `SearchConstraints.contactable_only` defaults to false. When true, discovery and planning require a safe supplied website/Instagram route; synthetic phones never qualify. `PurchasePlan.relaxations` is additive and defaults to an empty list. A suggestion contains `field`, `value`, `delta`, `base_revision`, full proposed `constraints`, eligible distinct-shop count and supporting offer IDs. It does not change state.

## Money and revisions

Monetary API values are **exact decimal strings**, not floating-point JSON numbers. Browser formatting uses `BigInt`. Unknown prices remain null; anomalous values are flagged rather than silently repaired. Mission writes carry `expected_revision` so an old preview or stale tab cannot overwrite a newer plan.

## Troubleshooting

| Symptom | Inspect | Correct next step |
|---|---|---|
| Catalogue is not ready | `/readyz`, importer result and configured path | Import the approved ZIP and use its generated catalogue; do not bypass hash validation |
| Page or assets missing | `frontend/dist` | Install locked frontend dependencies and build |
| AI status offline | Worker process, exact URL/token, Docker and heartbeat | Start the configured local worker; deterministic flows still work |
| Origin rejection | Browser URL versus `PUBLIC_ORIGIN` | Use the matching origin and restart with the intended configuration |
| No eligible shop | Budget/time/radius/payment, unknown facts and exclusion reasons | Explicitly change a constraint or confirm a scoped recheck |
| Stale preview/proposal rejected | Current mission revision | Use **تازه‌سازی برنامه** to read new proposals, preserving draft edits; accept deliberately again |
| Sample reset keeps your changed budget | Simulation reset semantics | Load **دیدن سناریوی نمونه** for original sample constraints |
| Model cleanup failure | Runtime fault and named task container | Follow [the fault recovery procedure](model-runtime.md); never delete the usage ledger or unrelated containers |

## Source map

| Path | Responsibility |
|---|---|
| `backend/torob/` | Catalogue, planner, mission store, AI boundary and HTTP API |
| `frontend/src/` | Persian workspace, cards/dialogs and exact-money presentation |
| `scripts/` | Import, local startup, worker, evaluation and packaging |
| `tests/`, `frontend/e2e/` | Domain/API/runtime and rendered regressions |
| `results/`, `docs/qa-evidence/` | Recorded measurements and verification artifacts |
| `data/` | Local generated catalogue/state/private packages; not public source |

No full catalogue, runtime database, private environment or Codex authentication should enter Git or a public image registry.
