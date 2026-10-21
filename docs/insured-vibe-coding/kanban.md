# Build kanban — Torob

_Last updated:2026-10-22. Next action: T3/T4 session-owned mission APIs and observation/recovery tests; implement grounded Codex turn flow._

## Doing
- Mission T3/T4 — session ownership, immutable constraints/revisions, seller observation lifecycle and deterministic recovery; grounded Codex turns. API-level real-flow QA is owed after routes exist.

## Todo
- Interface T5 — Persian mobile journey; written QA plus independent real-app pass.
- Deployment T6 — persistent cloud app and actual HTTPS model-worker roundtrip; includes outage/reconnect QA.
- Delivery — measured results, clean setup, five-minute demo, whole-branch independent review and submission artifacts.

## Done
- Catalogue T1/T2 — full validated import;123 total tests; real20-query/60-sample evaluation and exact demo primary/fallback checked. No UI surface; QA N/A, real import/search evidence in docs/qa-evidence/catalogue-*.json.
- Local model runtime M1/M2/M3-local — tests:63 passed, one upstream TestClient deprecation warning · QA: test-plans/model-runtime.md12✅/12 with docs/qa-evidence/model-runtime.json. Actual Codex responses9.496s/9.964s; running-container cancellation and cleanup verified. Hosted HTTPS acceptance remains a separate T6 gate.
- Repository isolation — independent repository, branch build/torob; no existing code affected. Initial baseline empty.
