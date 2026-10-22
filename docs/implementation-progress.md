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

## T2 — search and purchase planning

- Tests cover timezone/overnight/dummy-hour semantics, literal FTS queries, category/budget, exact large prices, source evidence, candidate/unknown/ineligible distinction, distinct-shop fallbacks, payment requirements, radius and selected primary. A red regression caught filtering price after retrieval limit; moved budget eligibility into SQL before limiting results. Another red regression required product minimum prices to cite the actual supporting offer.
- Real20-query benchmark and60 warm samples recorded in docs/qa-evidence/catalogue-evaluation.json; fixture independently matches the known primary/fallback and63.42m straight-line separation. These are source/fixture results, not stock or real purchase proof.
- Ruling: empty payment categories do not prove the selected product is covered; when payment is a hard requirement, such source evidence stays needs_verification. This conservative interpretation does not affect the main fixture, which has no payment requirement.
- T1/T2 local catalogue phase complete. T3/T4 starts next. Model integration, user-facing APIs/UI and deployment remain unimplemented.

## T3/T4 in progress — session/recovery APIs

- Implemented signed private sessions, persistent mission revisions, follow-up drafts, preview/confirm observations, mode isolation, explicit same-scope supersession, date-scoped closure, duplicate-shop quote suppression and deterministic plan deltas/history. Catalogue stays read-only.
- Regression: quoted price changes now recompute recorded payment amount/category eligibility; retaining the old supported flag could admit an ineligible quote. Payment conflicts bind the provider required when reported and stop applying if the user explicitly removes that requirement.
- Eight API boundary/persistence/recovery scenarios pass on top of domain tests. Actual HTTP/AI primary-flow QA and rendered UI remain owed; do not mark this phase done yet. Next: grounded asynchronous needs/explanation/reply turns using the real model queue, then written API QA.

## Actual-model QA findings and fixes

- Initial real API/model QA16/20 passed. All13 model calls returned schema-valid outputs; failures were our retrieval/context behavior, not provider access. No OmniRoute switch.
- N1: model emitted64GB/4GB while source uses Persian unit wording. Query-time literal unit variants now match both without changing source values. A later RAM wording miss added RAM/رم aliases and spec-key/section indexing; catalogue rebuilt atomically and source hashes unchanged.
- R1/R2: clarify branch discarded correctly extracted budget proposals, and the model lacked the selected product context. Proposals now survive clarification; owned-mission changes are explicitly proposals, never applied claims. Owned-mission budget turns retrieve the locked product by ID instead of asking the model to re-identify it. General discovery remains a separate turn without mission_id.
- C2: prompt asked for exact model names before trying a requested brand-level comparison. It now retrieves two source-backed examples first and forbids brand-wide quality claims. Selective real QA confirmed improvement; final reruns pending for changed N1/R1/R2 paths.
- Additional failure test: unverified Docker cleanup previously allowed another model start. Cleanup now verifies absence and persists a runtime fault latch across restart; it never silently assumes container removal.
- Live QA evidence retains all failed attempts as well as successful reruns. Do not mark the mission phase complete until the20-row ledger is green.

## T3/T4 acceptance

- Final independent mission API QA20/20 passed, including all10 actual Persian model cases.32 cited facts independently match the rebuilt source catalogue. Final N1/R1/R2 all preserve the exact product; proposed39M and41M budgets leave the40M mission unchanged and return applied:false. Real proposal preview counts0 and3 eligible shops respectively.
- Evidence includes failed initial attempts and retests,26 actual model starts across the QA series, no quota reset, and zero leftover QA servers/workers/containers. Real UI and hosted HTTPS gates remain separate. No provider switch: Codex failures were not observed; our retrieval/context defects were fixed.
- T5 starts with docs/ui-design.md. Ruling: frontend types will mirror the tested response contracts directly; these hand-written small interfaces plus TypeScript checks/real rendered-flow tests avoid generating a separate client framework. Any response drift must fail UI/API tests.

## T5 — rendered interface acceptance in progress

- Persian RTL interface built with local OFL-licensed Vazirmatn, real catalogue search/comparison, persistent purchase note, preview/confirm recovery, explicit constraint proposals and user-clicked handoffs. TypeScript/build and focused browser flows run; independent23-row UI acceptance still owed.
- Parent screenshot critique found the reply form scrolled buyers away from the plan. Ruling: native modal dialogs keep background controls inert, contain focus and return focus to the initiating control; successful confirmation focuses the revised mission. This changes presentation only. Red browser regression caught both missing dialog behavior and effect-cleanup focus timing; useLayoutEffect fixes focus restoration.
- Controlled delayed-transport regression caught cancellation before the initial AI POST returned. Request generations now discard/cancel late initial responses, with immediate pending progress/cancel controls. This controlled test is not a substitute for the independent real-worker QA rows.
- Repeated page reloads consumed the new-session creation allowance despite reusing the same session. A red API regression now distinguishes valid-session reuse (ordinary API rate limit) from actual new-session creation (10/min/IP). Existing creation-limit test stays green.
- Current full backend run before the last rate-limit fix:174 passed, one known upstream warning. Post-fix API suite and final phase checks will be recorded before completion. No cloud deployment or external publication yet.

## Container and delivery preparation

- Actual private Docker image built from pinned official Python3.12 ECR mirror after Docker Hub403; Liara mirror returned the same digest. First container boot failed because Docker COPY --chmod=444 also created its parent directory without traverse permission. Explicit directory0755 fixed it; the real container acceptance then passed. Failure log retained.
- Under512MiB/0.5CPU, actual full-catalogue search/recovery worked with no model worker. Session/observation revision survived restart, private paths returned404, catalogue SHA-256 stayed unchanged. Measured process peak59,980kB; docs/qa-evidence/container.json owns exact image/size/resource evidence. This is local acceptance only.
- Ruling: compile the frontend before image packaging and use a strict runtime allowlist instead of an extra Node build stage. Lockfile setup/build is reproducible; the application image needs no Node runtime. Cost if wrong: build-image script must be rerun after frontend edits.
- Private source-upload artifact includes the full catalogue but excludes state/authentication/.env/source-only files. Red→green packaging tests verify the allowlist and refuse missing or symlinked inputs. Final artifact must be rebuilt after any remaining fix.
- Eight deliberately adversarial recovery fixtures compare static price-first and static eligibility-first baselines with the same initial facts. Plan B8/8, static price0/8, static eligibility2/8; these are chosen cases, not population or purchase-success rates. Real source fixture confirmed+300000toman and63.42m separation. results/recovery.json owns timing and definitions.
- Current checks:178Python tests,3frontend exact-value tests, TypeScript/Vite build and Ruff pass. Independent UI QA is still running.
- Liara creation wizard rechecked: base Earth512MB/0.5CPU/5GB,750000toman/month,1040toman/hour beforeVAT; team credit2M. No app/key/disk created. Concrete proposal and open approval gate are in docs/deployment.md. GitHub authentication exists but no product remote/public repository has been created.

## T5 acceptance and fresh review fix pass

- Independent rendered UI acceptance23/23 passed with9 actual Codex starts (global ledger30→39), zero uncaught application errors, retained failure/retest evidence and actual read-only external handoffs. Parent visually inspected the mobile dialog/recovery screenshots. QA browser/contexts cleaned; the app and worker were restarted deliberately for user review.
- Fresh Astra xhigh read-only review found3 important issues and no critical/minor findings. All3 accepted: startup restore could overwrite a newer mission; backend60-exclusion truncation could hide the just-unanswered seller; raw turns persisted after queue payload cleanup.
- Fixes: user-interaction generation guards both restore success/failure; server prioritizes newest active observations before truncating exclusions in both plan branches;24h raw-model cleanup includes turns and runs at startup/heartbeat/capability/ordinary queue activity. Confirmed domain observations remain append-only by design. Backend regressions were observed red→green; the reviewer’s controlled Chromium repro established the restore defect, and maintained delayed-success/failure browser regressions pass after correcting an initial harness wait that captured the old ID too early.
- Final backend suite184passed; Ruff green. Private image rebuilt and actual container acceptance repeated, then source artifact rebuilt. New exact hashes/sizes live in their manifests. No re-review requested: focused regression proofs and full suite close the one fix pass.
- Rulings on reviewer declined-to-judge items: cloud approval/HTTPS remain open external gates; independent UI ledger owns rendered acceptance and is now23/23; real stock/contact/payment/ride fulfillment remains expressly outside the product claims. No minor findings were deferred.
- Native dialog keyboard ruling: browser-chrome traversal is allowed; underlying app controls stay inert, Tab returns into the dialog, Escape/focus return and full mobile keyboard flow were verified.
- Upstream font license is retained verbatim, including its original trailing whitespace; no authored whitespace error is being waived.
- Local implementation is ready for review/use. The overall contest entry is not complete: hosted acceptance, public source/video and submission remain pending. Liara work proceeds under the user’s instruction to continue the second product at a blocker.

## Shared launch cancellation correction

Independent Liara cleanup QA found a CREATED model container that appeared after an early absence check during cancellation. The shared copied adapter now acknowledges Docker creation before the cancellable start/attach phase; uncertain creation latches cleanup failure. Both new regressions passed in this repository, and the full backend suite is186passed. No domain shopping/transport behavior changed. The reproducible official runtime image and current VAT-inclusive provisioning quote are in docs/model-runtime.md and docs/deployment.md. The local worker was restarted after confirming no active model container; the global usage ledger was preserved. Hosted acceptance still remains pending.

## Public source publication — 22 October

The user explicitly authorized creating and pushing both repositories in the logged-in GitHub account. Published this independent source repository under milad-afkhami on main; submission.md owns its URL and source identity. Anonymous page/README/API checks and remote commit equality are recorded in docs/qa-evidence/source-publication.json. Full catalogue, private archives, environment/authentication and runtime databases remain excluded. No code changed for publication; existing test results are unchanged, not newly rerun. Cloud acceptance, narrated video and submission remain open.

DECISION: use a standard main branch in the new repository and preserve the local build branch. Why: these are new owner-authorized repositories with no existing collaborators, workflows or deployment triggers. Alternative: a feature-only remote would leave the requested source repository less accessible. Recoverable: retain the original build branch; ordinary future commits update main without rewriting history.

DECISION: use HTTPS with the existing GitHub CLI credential helper per push. Why: the initial SSH attempt failed host-key verification; HTTPS succeeded without weakening SSH verification or changing global authentication settings.

## Familiarization walkthrough verified — 22 October

The existing app8651 and outbound model worker remain running; actual capabilities reported catalogue_ready/model_available true with codex_cli. A fresh isolated rendered session loaded the fixed source-row simulation, inspected the inquiry, manually previewed/confirmed unavailable, observed the300,000toman fallback promotion and verified the updated destination chooser. Reset the session’s simulation afterward and closed the controlled browser. No external navigation/contact, provider change or code change occurred. This is a rehearsal flow check, not a newly rerun aggregate test suite or hosted acceptance.
