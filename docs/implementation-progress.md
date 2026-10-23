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

## Public documentation experience

Expanded the public README into a product/judge entry point with a verified local screenshot, capability/status tables and a Mermaid journey. Added a documentation map, reproducible getting-started guide, screen-by-screen user guide and configuration/API/troubleshooting reference. Architecture diagrams separate model authority, deterministic code and provider/hosted acceptance. Recorded results link to their evidence; local fixture behavior is not promoted to live integration. Documentation verification is separate from unchanged application tests.

Documentation checks passed: local links/anchors and fenced blocks, non-placeholder shell syntax, all running OpenAPI routes covered by the reference, and 5 Mermaid diagrams parsed/rendered in a browser. The README preview loaded its actual screenshot without horizontal overflow at1280px. docs/qa-evidence/documentation.json records this local renderer proof; it does not claim exact GitHub visual parity or newly rerun application suites.

## User-directed product revision and blind judging

Agent-led Persian workspace — 191 backend tests,3 exact-value tests,13 actual browser regressions; documented keyboard/focus/select/checkbox and source-row recovery. Blind source/output review improved214→235/300 (simulated, not official). One-call condition update18.4seconds with exact confirmation; Figma community-kit adoption qualified in docs/design-system.md. Previous private deployment artifact predates this revision; rebuild before live acceptance. Source snapshots deliberately excluded implementation docs/README/plans; judges exercised actual output against the original brief and re-evaluated after fixes. docs/qa-evidence/blind-judging.json owns the recorded review/measurement scope. Final verified application suites are recorded above; upstream Starlette/httpx warning remains known.

DECISION: retain a single responsive desktop/mobile implementation, with the agent as first mobile action and manual search/filters in a disclosure. Why: mobile is the main in-person use case, desktop adds little separate maintenance and supports review. Alternative: a separate desktop product was rejected. UI controls use a small shared accessible component vocabulary; ss01 is font shaping, not a replacement for exact money parsing. Plan B is our chosen name, not organizer branding.

The initial custom select test caught label activation reopening the popover and Escape closing its modal; both were fixed. Delayed notebook focus now respects a user who moved to another control. Two simultaneous browser runs caused localhost session429/artifact collisions; QA now reuses one actual anonymous sign-in across isolated contexts, leaves production limits unchanged and runs serially. Final13-browser run passed. A previous test expected a second model recommendation for an owned mission; it now verifies the single interpretation plus unchanged mission until explicit confirmation. The missing old worker was restarted without resetting its80-start ledger; subsequent genuine one-call proof passed.

## 23 October — purchase completion pass

DECISION: Add deterministic budget/radius-only suggestions that are proved to unlock at least one candidate for the same product and require explicit acceptance. Do not remove payment/hours/contact requirements automatically. Alternatives rejected: LLM guessed relaxations and a multi-condition recommendation that hides tradeoffs. Reversible through normal condition editing.

DECISION: Location search selects an actual catalogue address/coordinate as a reference point; no fabricated neighborhood centroid/geocoding. Comparison aligns source spec keys and adds same-condition local feasibility. The agent remains the first input and existing controls remain available.

Execution: red→green domain/API tests, then UI wiring and planned rendered QA; root owns deployment/artifacts and final blind review. Scope ends at a runnable, verified phase rather than cosmetic score inflation.

Purchase completion phase evidence:205 backend tests,3 exact-value frontend tests,21 real-browser regressions passed; Ruff, TypeScript/Vite and whitespace checks passed. One unchanged upstream Starlette TestClient/httpx deprecation remains. Actual full-catalogue address selection, contactable discovery, budget/radius acceptance, comparison, empty search and startup recovery exercised on isolated8671. No model calls, budget resets, seller messages, main-app restarts or cloud operations performed.

DECISION: Exact compact model equality ranks before accessory FTS hits before the SQL retrieval limit; categories remain retrievable. This fixes actual A07 results that previously led with cases and screens rather than phone variants. Model recommendation facts now prioritize stored RAM/storage/battery/camera specifications while preserving original evidence indexes; nothing is inferred from brand/model names.

QA discovery and correction: the initiating control was captured after asynchronous mission creation, allowing a late notebook reveal to steal focus from a later comparison checkbox. The delayed-POST regression failed before capturing the original trigger and passed after; all prior browser journeys pass. Source-only review and deployed acceptance remain separate gates owned by the root workstream.

## 23 October — independent review repair batch

Verified the reviewer’s concrete defects before repair: comparison used contact-filtered search prices as global prices; fresh planned visits had an hours opt-out default; equivalent source RAM keys split; failed comparison mixed unknown/zero/loading states and lacked retry; stale suggestions were safely rejected but had no in-page refresh. Four actual-browser regressions failed on the prior output, then passed after the coherent repair. RAM/storage alias tests preserve source labels, source values and incompatible-unit separation, including attached numeric units.

DECISION: Global comparison prices use fresh authoritative exact-product objects; the condition-compatible offer remains a separate row. Do not add a “filtered search price” row from old cards, since a person may change filters after retrieval. Alternate rejected: relabeling stale incoming card prices as a current contact minimum.

DECISION: Fresh planned visits require declared-hours compatibility by default. Existing/restored explicit unchecked choices remain unchecked. A stale write offers an explicit current-plan read, never a retry of the mutation or an automatic acceptance, and leaves unsaved form edits intact. Readable origin labels persist alongside exact coordinates; manually editing coordinates removes a potentially misleading label.

Verification inventory:206 backend tests and6 frontend exact-value/alias tests pass. The first expanded browser sweep23/25 identified the earlier contact test’s obsolete implicit hours opt-out and a functional-test burst hitting the unchanged180/minute API limit. A second fast sweep plus an accidentally overlapping targeted run also hit the throttle/artifact contention. Changed approach: only one serialized Playwright run, paced client requests every400ms; no server limiter, model budget, clock or state reset. Genuine load/hosted acceptance remains separate. Final full-sweep evidence is recorded below only after completion.

Final review-repair gate:206backend tests,6frontend value/alias tests and26/26canonical browser journeys pass; Ruff, TypeScript/Vite and whitespace checks pass. Source SHA-256 map and exact commands are in qa-evidence/purchase-completion.json. The serialized paced run uncovered a genuine pending-demo draft overwrite; the controlled delayed-source-GET test failed before locking the manual form during busy operations and passed after. No production rate or model usage limit was changed/reset. Root owns targeted independent re-review, main/hosted rollout, genuine model verification and publication.

Origin-race follow-up: reviewer reproduced an origin selected during a held condition PATCH being replaced by its older response. A controlled actual-PATCH/Tajrish-picker regression failed before guarding draft replacement by the initiating edit epoch, and passed afterward. The same class was reproduced and guarded in late sample loading. Accepted mission and newer draft remain distinct; no automatic second write. Full28browser and6frontend checks, final TypeScript/Vite build and whitespace pass. Source/dist are frozen for root packaging; hashes are in qa-evidence/purchase-completion.json.origin_race_followup. No backend/deployment changes, model calls, commits or pushes were made.

## 23 October — bounded discovery continuation

Approved contract: optional discovery_parent_turn_id validates an exact recent owned completed needs/no-mission turn; up to six prior cards retain actual display order and source IDs.30-minuteTTL is an assistant-selected conservative default, not an organizer rule. Exact comparison fetches allowed IDs rather than re-searching names. Ambiguous “more memory” asks RAM versus storage; mission product/conditions never change without explicit selection/acceptance. Frontend clears continuation on manual search/sample/result replacement. TDD rejection matrix and controlled fixture-worker rendered QA precede freeze; no genuine model/cloud calls in this owner pass.

Discovery continuation implementation verified:233backend,6frontend and32browser checks pass, plus Ruff/TypeScript/Vite/whitespace. Dynamic reference IDs resolve exact prior display order, not recommendation order; cross-owner/expired/failed/reply/mission parents fail before enqueue. Source review caught and closed a missing-reference fallback that could guess new searches, and a late completed turn that could reattach its parent after sample replacement; both received failing regressions before fixes. The checked-in deterministic fixture server exercises real HTTP/session/domain paths without genuine model calls; root still owes live model/hosted two-turn acceptance. Source/dist hashes and boundaries: qa-evidence/discovery-context.json. No private archive, cloud resource, source commit or push was produced in this phase.

Independent review reopened the continuation release for three shared boundary failures: prompt truncation was reused as display state, a narrow word-only reference parser permitted unbound fallback, and diagnostic acceptance omitted the existing cancellation epoch. A complete clarification/reference/manual-entry matrix reproduced15backend failures plus the actual rendered stale diagnostic overwrite before repair. Full typed parent snapshots now survive every clarification, independently of the six-card prompt allowlist; original filtered prices/offer evidence also stay intact (separate200→100regression). ASCII/Persian/Arabic numeric positions and same-model hints bind exact source cards or clarify. Manual diagnostics and sample loading invalidate pending turns before replacing cards. Independent re-review then found exact-reference comparison still copied global get_product prices into the preserved card list. Both comparison orders reproduced that same scope drift before repair. Preservation now belongs to one terminal _result projection, not branch assignments: all clarification/degraded exits return full original typed snapshots; exact comparisons verify source IDs then select original snapshots in requested order; successful new retrieval retains its separate source contract. All get_product consumers were audited, and the six-exit clarification matrix also asserts filtered prices/evidence. Verification:256backend/6frontend/Ruff/TS/Vite/whitespace; canonical browser inventory32passed with one test-only cancel-observer error, corrected, then all5affected browser cases passed against the final backend. No model/cloud/package/commit/push calls were made; root owns independent retest and genuine hosted acceptance. Current evidence and final hashes remain in qa-evidence/discovery-context.json.

## 23 October — completed-result polling transport recovery

The actual hosted demo completed its typed reply server-side but a polling network failure discarded the active browser turn before preview rendering. A controlled aborted-GET browser case reproduced the missing preview before repair. Transport failures now have a precise type, and only the exact owned turn GET can retry: three retries shared across the whole turn, original monotonic120s deadline with remaining-time fetch abort, cancellation/epoch checks before and after reads/backoff. HTTP502/503/504 are eligible; authentication/ownership/revision/rate-limit/application failures and all POSTs remain single-attempt. An additional native hanging-fetch test caught fractional timer rounding permitting one extra read; a terminal deadline-abort latch closes that path without moving the deadline. The full canonical frontend suite22/22 and rendered suite37/37 passed, including same-preview/single-POST, persistent-failure bounds, cancel during backoff and no creation replay. After the latch-only change, all four affected polling browser cases passed again. TS/Vite/Ruff/whitespace passed; backend remains unchanged with its prior256test evidence. Source/dist and precise hashes are frozen in qa-evidence/polling-recovery.json; root owns new artifact/hosted acceptance. No model/cloud/package/commit/push activity was performed by this owner.

## Delivered hosted flow and narrated artifact —23October

Final reviewed source44f56c7 is public-CI-passing and actually served by release6adae318bffb36d784d979c4.256backend evidence is reused for unchanged backend;22frontend/37browser checks and final affected polling retests pass. Independent source/browser review covers exact-turn retry bounds, cancellation, terminal status, original deadline and no POST replay. Actual old-session mission state survived the final source transition.

Genuine hosted needs, exact ordinal comparison, reply preview and confirmed300000toman recovery passed; two naturally observed network changes recovered. A separate controlled completed-result response drop recovered the same observation with one genuine turnPOST, zero confirms and unchanged mission. The fixed one-attempt breadth evaluation used exactly six audited starts and retains3passes/1explanationtimeout after74.7seconds; no criteria/prompt replay or ledger reset.

The public304.812-second narrated video has reviewed actual footage, labelled synthetic voice and a same-persisted-mission recording join. Independent media review caught an incorrect leading trim that hid the budget proposal; corrected visual source bounds restore39.4M/no-match/+100k/explicit acceptance. Original failure/edit retained; final hash and anonymous playback live in submission.md and demo-manifest.json. Neither the standalone provider restart nor contest submission is falsely marked complete.
