# Implementation progress and rulings

## Current mandate

Implement Torob fully, then Liara; move to Liara if Torob has a confirmed external blocker after independent work is exhausted. User explicitly enabled Insured Vibe Coding, Testing Philosophy and Autohelm. OmniRoute is an authorized fallback if Codex performs poorly. Product implementation began22 October2026. No cloud resources or API keys created yet.

## Decisions

- DECISION: use the requested new sibling repository on build/torob; no linked worktree is needed because this is an empty independent repository with no existing branch/work to protect. Alternative: nesting a worktree would obscure the requested product location. Reversible: ordinary branch/worktree creation later.
- Ruling: canonical plans stay in the private planning repository; this repository tracks actual phases/evidence instead of copying the entire private context. The executor ledger lives in .superpowers/sdd/torob-plan; durable evidence/rulings stay here and in the kanban so compaction cannot lose progress.
- Ruling: OmniRoute replaces the former no-alternative-provider restriction only under the user's latest conditional authorization; any actual switch must be explicit in configuration/results, never mislabeled Codex.

## Evidence

- P0: both proposed product paths were absent; Python/uv, Node/npm and Docker are available. No baseline application tests exist.
- Dependencies: M1 produces the ModelRequest/ModelResult/client for T3; M2 job lifecycle feeds session-owned turn state; T1 catalogue feeds T2/planner; T4 overlays never mutate catalogue. No interface conflict found in the final reviewed plan.

## M1 — model client

- RED:20 tests failed for missing runtime implementation. GREEN:26 meaningful scenarios pass, including real subprocess timeout/cancel,100-request shared budget, schema/evidence rejection and credential exclusion. Additional red regression proved NaN/infinite deadlines passed validation; finite-only validation fixes both.
- Actual isolated application call: `docs/qa-evidence/model-smoke.json`, Codex CLI0.163.0 / gpt-6.1-sol,9046ms, valid Persian HOLD. Model-only smoke does not establish shopping intelligence. No OmniRoute switch needed.
- Decision: use the existing pinned official OpenResty image as a neutral container filesystem for the static CLI, overriding its entrypoint; it runs no web server. Alternative: another image download adds no demonstrated benefit. Production configuration requires an explicit image digest.
- No UI surface for this library phase; planned UI QA N/A. Full running-container cancellation verification remains to be recorded alongside worker QA; process cleanup behavior has automated real-process tests.

## M2 — job transport / worker

-57 tests passed before QA, covering real SQLite leases, private worker authentication, replay/expiry/cancel, session quotas, typed provenance and outbound worker behavior. Coverage was91% across current runtime modules; missing scenarios are reviewed by risk, not waived by that number. Upstream Starlette emits a TestClient/httpx deprecation warning; no runtime failure, not hidden.
- Tests exposed same-timestamp queue ordering by random UUID: fixed to insertion order. A second red regression exposed late lease results reported as completed by the local worker: now discarded. Owner stop propagates cancellation during inference.
- A reservation holds the shared local CLI lock before claiming a hosted job without spending quota until an actual call starts.100-start rolling ledger persists across requests and both products.
- Dedicated QA is running the production HTTP router, actual isolated Codex and on-disk queue against `docs/insured-vibe-coding/test-plans/model-runtime.md`. Runtime phase remains Doing until all owed rows have evidence.

## Local runtime acceptance / next phase

- Independent real QA12/12 passed; evidence inspected by parent. Includes actual Uvicorn TCP, persisted SQLite, three isolated Codex starts (two complete, one canceled),46-second disconnect,16-second expiry, lease/auth/payload boundaries, contention and reconnect. Server/containers cleaned; no hosted HTTPS/product UI claim. Full current tests:63 passed, one documented upstream deprecation warning.
- Local runtime phase complete; T3 domain schemas/turn APIs and T6 actual-hosted acceptance remain unimplemented.
- Catalogue phase started: source ZIP inspected for actual headers/JSON shapes; CSV uncompressed sizes products196,150,238 bytes, offers79,945,479, shops9,202,900. T1 will stream and atomically replace the generated catalogue; full raw data remains Git-ignored.

## T1 — complete real catalogue import

-91 total tests pass (28 importer/normalization cases plus runtime). The first full-data run failed on two empty product titles, proving the stricter inferred requirement wrong. A red regression now preserves empty/missing titles without fabrication or dropping products; interfaces must label them unknown.
- Real import succeeded:6476 shops,225903 products,331506 offers; all three payload hashes match, foreign keys and SQLite quick_check pass.42.296s,655,405,056-byte database, peak RSS29,192KiB. Source null counts match previous research.909 prices flagged by precision/zero/comparative quality rules; this is a data-quality flag, not proof of incorrect source prices. Raw values remain preserved. Evidence: docs/qa-evidence/catalogue-import.json.
- Ruling: one median price per distinct shop (itself the median of that shop's normal offers) prevents duplicate offers from dominating the cross-seller anomaly comparison. Exact Fraction arithmetic avoids float rounding. Alternative: count every offer, which overweights duplicate shops.
- No UI surface; QA N/A for importer logic. Actual full import/read/integrity is the integration evidence. T2 search/hours/eligibility/planning next.
