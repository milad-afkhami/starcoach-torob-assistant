# Model runtime

The hosted app queues bounded, sanitized model requests. The local worker pulls them over HTTPS and returns validated JSON. Personal Codex authentication stays local. The model container has no Liara credentials, worker bearer or application database. Search and deterministic recovery remain usable when the worker is absent; actual local acceptance is recorded separately from hosted checks.

## Local setup

Use Python3.12, Docker and the installed Codex CLI static binary. Run `uv sync`, copy `.env.example` to a private `.env` and set the listed values. CODEX_BINARY_PATH must point to the static executable, not the Node launcher. CODEX_IMAGE is an explicitly trusted pinned digest; the entrypoint is overridden, no image service runs. The existing local smoke used CLI0.163.0 and gpt-6.1-sol. A lockfile pins Python dependencies.

The application and worker share a separately generated256-bit bearer secret. The browser never receives it. Set the hosted value through the provider secret configuration, the local value in private runtime configuration, and never pass the value as a command argument. This worker exposes no inbound port.

Run from the repository root:

```bash
uv run --env-file .env python scripts/model_worker.py
```

Stop with Ctrl+C or SIGTERM. The worker propagates cancellation and removes the named model container. Starting it again never replays a completed/canceled/expired lease. The host marks model access unavailable45 seconds after its last heartbeat. Configured local tests can set MODEL_WORKER_LOOPBACK_TEST=1 with an actual loopback HTTP origin; public HTTP origins remain forbidden.

## Bounds and failure behavior

- One CLI process across both entry clients; a private filesystem lock and rolling24-hour ledger at `/tmp/starcoach-codex-<uid>` limit starts to100, including failed attempts and correction calls. Operator-owned configuration may deliberately change the ceiling; browser/model input cannot. Do not delete the ledger as an automatic quota workaround.
- One leased job and two queued jobs; one outstanding job per user session, ten new model requests per session per hour, at most two model calls per request. Session rotation does not bypass the local global call budget.
- Queue claim deadline15 seconds, CLI60 seconds, outer request120 seconds, lease65 seconds bounded by outer expiry. A reply that arrives late or for an old mission cannot apply to the current plan.
- Request evidence≤48KiB, worker HTTP body≤64KiB, final output≤16KiB. Only server-owned schemas and application tools are supported. No arbitrary shell/SQL/URL tool or external seller message.
- Missing credentials, malformed output, exhaustion or expiry is an explicit failure. Codex results are never silently replaced with fixture output. The user permits an explicitly recorded OmniRoute fallback if actual Codex behavior is unsuitable; no switch has been made. Production OmniRoute would require its own provisioned secret.

## Verification

`uv run pytest -q` exercises model validation, usage/cancellation, SQLite job lifecycle, private worker routes and outbound behavior. A separate real HTTP/container QA pass is tracked in `docs/insured-vibe-coding/test-plans/model-runtime.md`; check its actual evidence/status before claiming completion. The successful direct live model probe is in `docs/qa-evidence/model-smoke.json`.

A local server roundtrip does not establish hosted connectivity. T6 must repeat genuine Persian interaction, disconnect/reconnect and deterministic recovery on the actual public HTTPS deployment. Personal auth must not be uploaded to cloud hosting to bypass that gate.

If container disappearance cannot be confirmed, the runtime writes an owner-only runtime-fault.json beside its shared lock and stops accepting new model calls. The worker stops heartbeating, so hosted AI availability expires normally. Inspect the named task container and Docker state, verify absence, then preserve/clear that fault record deliberately before restarting. Never clear the usage ledger or remove unrelated containers as a recovery shortcut.

## Raw model-data retention

After24hours, queue input/result copies are cleared and application turn request/context/result rows are deleted. Cleanup runs at startup and during ordinary queue activity, worker heartbeats and capability checks; an idle stopped service purges on its next startup. Timing/state/model provenance in queue metadata remain for accounting. Confirmed seller observations are a separate append-only mission history and are not silently erased by model-turn cleanup; their user-reported/simulation provenance remains explicit.

## Launch acknowledgement correction

Independent Liara runtime QA found a shared launch-cancellation race: a Docker container could finish creation after an early cleanup/absence check. Both copies now await bounded create acknowledgement before cancellable start/attach. Unknown creation faults closed and keeps the shared budget intact; cleanup remains explicit. The final reproducible image is `public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70`, with the entrypoint overridden by the mounted executable. A genuine corrected-adapter schema call passed on this already verified official base; local runtime retest is recorded separately from hosted acceptance.

## Selected-product condition updates

A needs request on an existing selected-product mission now ends after one validated interpretation call. Radius, explicit Tehran visit, payment and opening-hour changes remain proposals, and deterministic code returns the actual eligible-shop count in toman-based source data. Discovery/comparison may still use two calls. This avoids re-recommending an already selected product and prevents model prose contradicting computed eligibility. The independent final rehearsal measured18.4seconds for this one-call path; it is a measured local run, not a latency guarantee.
