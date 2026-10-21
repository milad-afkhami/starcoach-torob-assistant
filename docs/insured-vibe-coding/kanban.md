# Build kanban — Torob

_Last updated:2026-10-22. Next action: T1 importer tests against actual CSV headers, then full catalogue import._

## Doing
- Catalogue T1/T2 — atomic streamed import, exact money/provenance, Persian FTS search, declared-hours/payment/geo eligibility and distinct-shop planner. No UI yet; real import/search acceptance still owed.

## Todo
- Mission T3/T4 — grounded model tools, session ownership, observations and deterministic recovery.
- Interface T5 — Persian mobile journey; written QA plus independent real-app pass.
- Deployment T6 — persistent cloud app and actual HTTPS model-worker roundtrip; includes outage/reconnect QA.
- Delivery — measured results, clean setup, five-minute demo, whole-branch independent review and submission artifacts.

## Done
- Local model runtime M1/M2/M3-local — tests:63 passed, one upstream TestClient deprecation warning · QA: test-plans/model-runtime.md12✅/12 with docs/qa-evidence/model-runtime.json. Actual Codex responses9.496s/9.964s; running-container cancellation and cleanup verified. Hosted HTTPS acceptance remains a separate T6 gate.
- Repository isolation — independent repository, branch build/torob; no existing code affected. Initial baseline empty.
