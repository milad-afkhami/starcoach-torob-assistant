# Actual HTTPS deployment

[← Documentation](README.md) · [User guide](user-guide.md) · [Getting started](getting-started.md)

The full-catalogue application is live at **https://torob-plan-b-2026.liara.run**. It uses one disposable Liara application, an isolated contest network and a persistent state disk. Codex authentication stays on the local outbound worker; it is never uploaded to Liara.

| Part | Demonstrated configuration | Evidence |
|---|---|---|
| Public application | Docker, one replica, port8000;512MiB/0.5CPU base plan | [Actual hosted acceptance](insured-vibe-coding/test-plans/hosted.md) |
| Catalogue | Private immutable image;6,476shops/225,903products/331,506offers | [Packaging](packaging.md) and [artifact manifest](qa-evidence/deployment-artifact.json) |
| State |1GB disk named `state`, mounted at `/data` | [Hosted recovery](qa-evidence/hosted-offline.json) |
| Model | Managed local worker, outbound HTTPS to the hosted job queue | [Genuine needs/reply](qa-evidence/hosted-model.json) and [reconnection](qa-evidence/hosted-reconnect.json) |
| Browser boundary | Secure/HttpOnly/SameSite=Strict cookie, independent-session404, wrong-origin403, private paths404 | [Hosted boundary checks](qa-evidence/hosted-offline.json) |

```mermaid
flowchart LR
    Buyer[Buyer browser] -->|HTTPS| App[Liara application]
    App --> Catalogue[Private immutable catalogue]
    App --> State[Persistent state disk]
    Worker[Local isolated Codex worker] -->|Outbound HTTPS job transport| App
    Worker --> Codex[Local Codex authentication]
```

## What was actually exercised

Actual HTTPS acceptance covers the source-data purchase scenario, manual recovery with the worker disconnected, a genuine Persian needs request, genuine interpretation of an explicitly simulated seller reply, preview before confirmation, exact300000toman fallback delta, mobile layout and session/origin isolation. Deliberate worker disconnection was followed by a fresh genuine request after reconnection. These are narrow recorded runs, not continuous-availability or concurrency guarantees.

The provider accepted a single restart request with HTTP200, and the existing session/mission remained readable. Its history response did not independently establish that a container restarted. [The restart record](qa-evidence/hosted-restart-result.json) therefore remains **partial**, rather than promoting HTTP continuity to proof of a restart. The separately recorded [version-transition test](qa-evidence/hosted-version-transition.json) owns the subsequent source-version/state-continuity result; an awaiting or failed record is not a pass.

## Current deployed version

Release `6adba2477ebf55567ce5ac44` serves runtime source `f0c1f099ec3b3400986122dd2eb77182224168c1`: semantic continuation from `5119f12`, followed by the scoped map-loading fix. The 323,443-byte private package has SHA-256 `26b7aa55dea59249a202e3c24267d9bfd5ea70ab304811d1bc03d259c01c2c8e`. Its build-stage download validates the exact organizer archive, three payload hashes and full counts; runtime startup downloads or rebuilds nothing. [Current artifact](qa-evidence/deployment-artifact.json) and [integration evidence](qa-evidence/r2a/integration.json) own exact identities.

[Final hosted acceptance](qa-evidence/r2a/r2a-final-hosted.json) verifies actual HTML/JS hashes, the previously recovered guest mission, two source markers and ten decoded real basemap tiles without stale warnings, compact mobile controls, private-path denial and no page errors. It makes zero model calls. [Genuine hosted discovery](qa-evidence/r2a/hosted-genuine.json) passed on the identical semantic backend before the map-only patch; a separately declared [hosted refinement](qa-evidence/r2a/hosted-continuation.json) expired before a validated result. Neither result is relabelled as inference on a later full artifact.

The first semantic build timed out while copying the full catalogue after download/import/dependencies. A distinct bounded release using its already accepted source succeeded; the failed release and both older unknown large-upload intents remain retained. The final map package received its own accepted source and release. [Provider failure](qa-evidence/r2a/provider-build-negative.json), [intermediate artifact](qa-evidence/r2a/deployment-artifact.json), and [final map artifact](qa-evidence/r2a/deployment-artifact-map.json) remain separate.

## Reproducible private source packaging

Build the catalogue and frontend using [getting started](getting-started.md), then use the allowlisted packaging script. The current compact mode fetches and validates the pinned organizer dataset only during image build. The earlier complete-CSV and compressed-SQLite/XZ modes remain documented alternatives; their transport hashes and semantic-equivalence evidence stay distinct. The private source artifact is below the provider's128MB upload limit. State, private environment files, personal records and Codex authentication are excluded. The final image contains the mandatory catalogue and must not be pushed to a public image registry.

An initial144MB archive was rejected at upload. A later archive exposed a legacy-builder incompatibility with `COPY --chmod`; the corrected Dockerfile uses ordinary `COPY` plus `RUN chmod`. These failures and the successful actual legacy build are retained in [packaging evidence](qa-evidence/packaging-legacy-compatibility.json). Runtime startup prepares only the opened state directory, then drops to UID/GID10001 with zero effective capabilities and `NoNewPrivs=1`. Both constrained named-volume and root-owned-bind local acceptance passed.

`docker compose up -d` remains the local container route. Set a private generated session secret, worker token and exact public origin for that environment; do not reuse cloud credentials. The local Compose URL is `http://127.0.0.1:8652`; the development app uses8651. The worker must target the same chosen application URL.

## Local review runtime

The loopback mirror at `http://127.0.0.1:8651` uses `starcoach-torob-preview.service` and `starcoach-torob-preview-worker.service`, private `.env` and the existing local state. Its backend has the revised semantic contract and its canonical assets match the current map build. The separate `starcoach-torob-model-worker.service` serves the public app. All workers and the private Liara operator share the persistent 100-start rolling 24-hour gate and single-process lock; no limit or ledger was reset. Isolated QA fixtures are stopped. Credentials and state remain private.

## Resource scope and lifecycle

The inspected base/basic plan quote was1146toman/hour includingVAT:55008toman for48hours for this app. Combined with the two disposable Liara scenario services, the quoted total is165024toman, within the reviewed200000toman scope. Quotes are not measured charges, a guarantee about retained-disk billing or a current balance. No personal top-up, plan upgrade or unrelated application overwrite was performed.

A best-effort local timer is armed for25October2026 at00:00UTC to request scale zero for only the three recorded disposable app IDs, preserving data. It depends on this workstation/session/network and is not a provider-enforced billing cap. The managed local worker also depends on this workstation and its authenticated Codex session. Deterministic search/recovery remains usable when the worker is unavailable; hosted AI is not promised to be always on.

Sources: [Docker deployment](https://docs.liara.ir/paas/docker/how-tos/deploy-app/), [persistent disks](https://docs.liara.ir/paas/docker/how-tos/use-disk/), [quota-based disk creation](https://docs.liara.ir/paas/disks/create/), [public pricing](https://liara.ir/pricing/). The actual account-specific scope/quote was inspected separately; credentials and private provider receipts remain outside the public repository.
