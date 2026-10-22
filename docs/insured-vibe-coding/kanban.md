# Build kanban — Torob

_Last updated:2026-10-22. Next action: independent23-row rendered UI QA; fix failures, then container/deployment and delivery. Local app http://127.0.0.1:8651; actual model worker connected._

## Doing
- Interface T5 — Persian search/needs, comparison, persistent primary/fallback mission, confirmed reply recovery and external handoffs; rendered UI QA owed.

## Todo
- Deployment T6 — persistent cloud app and actual HTTPS model-worker roundtrip; includes outage/reconnect QA.
- Delivery — measured results, clean setup, five-minute demo, whole-branch independent review and submission artifacts.

## Done
- Mission T3/T4 —169 total tests; real API QA20✅/20 including10 actual Persian model scenarios,32 facts checked. Initial failures fixed and retained in evidence. Rendered UI still owed in T5.
- Catalogue T1/T2 — full validated import;123 total tests; real20-query/60-sample evaluation and exact demo primary/fallback checked. No UI surface; QA N/A, real import/search evidence in docs/qa-evidence/catalogue-*.json.
- Local model runtime M1/M2/M3-local — tests:63 passed, one upstream TestClient deprecation warning · QA: test-plans/model-runtime.md12✅/12 with docs/qa-evidence/model-runtime.json. Actual Codex responses9.496s/9.964s; running-container cancellation and cleanup verified. Hosted HTTPS acceptance remains a separate T6 gate.
- Repository isolation — independent repository, branch build/torob; no existing code affected. Initial baseline empty.
