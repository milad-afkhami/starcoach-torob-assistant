# Torob whole-local-implementation review

Reviewed repository: `/home/milad/Desktop/projects/starcoach-torob-assistant`.

Reviewed range: `df8cfef..6311083`; checked-out HEAD was `6311083c446225a0db5f10a0f2c4ce193be0cbdc`. Review was read-only on repository source, index and branch. Reproductions and browser evidence are under `/tmp`. Existing untracked independent UI QA/submission artifacts were not edited.

## Strengths

- The catalogue is imported atomically and opened read-only, preserves original records, performs exact integer price arithmetic and identifies comparative anomalies without silently repairing source values. Distinct-shop planning and explicit eligibility states prevent duplicate offers, missing prices and unknown hours from becoming nominally valid backups.
- Mission ownership, optimistic revisions and preview confirmation are enforced in transactional storage. Model-produced observations remain previews; simulation provenance derives from the stored mission. Recovery is deterministic and keeps the selected product and purchase constraints.
- The model worker has a separate bearer boundary, bounded queue/lease/call lifetimes, a persistent global start budget, isolated child mounts and verified container cleanup with a fault latch. The deployment package uses an explicit runtime allowlist, and local persistent-state container evidence is clearly distinguished from hosted acceptance.
- I independently ran the current Python suite with bytecode/cache writes disabled: **178 passed, one existing upstream Starlette/httpx deprecation warning**, in 21.10 seconds.

## Issues

### Critical

None found.

### Important

### 1. A delayed startup restore overwrites a mission the buyer has just selected

**Location:** `frontend/src/App.tsx:71–73`, with `accept` at lines 54–57.

Initialization enables shopping controls as soon as capabilities return, then asynchronously retrieves the saved mission. Its eventual response is accepted whenever the component is still mounted; it does not check whether the buyer has selected another product, created a new demo/assisted mission or edited the draft in the meantime. `accept` also writes the stale mission ID back into localStorage. A slow saved-mission request therefore silently replaces a newer selected product, constraints and mode. A failing delayed restore can similarly remove the newer saved ID in its unconditional error path.

**Reproduced:** `/tmp/torob-review-browser.mjs` loads the actual compiled React interface in headless Chrome with controlled API transport. It starts with `old-mission` in localStorage, holds the startup GET, clicks the demo button, waits until `NEW_SELECTED_PRODUCT` is visible, and then releases the old response. The visible selected product changes to `OLD_RESTORED_PRODUCT` and localStorage returns to `old-mission`. Screenshot: `/tmp/torob-review-restore-race.png`. This is a controlled asynchronous UI regression, not real-model or hosted acceptance.

**Impact:** An ordinary slow reload can discard the buyer's latest selection and show the wrong purchase plan without a deliberate product/constraint change. This violates T3/T5's stale-response and explicit-selection guarantees.

**Fix direction:** Finish restoration before enabling dependent shopping actions, or use a mission/draft operation generation checked on both successful and failing restore responses. Invalidate the restore when newer user work begins. Cover delayed success and delayed failure with regression tests.

### 2. Truncating excluded offers can remove the only seller the buyer must recheck

**Location:** `backend/torob/planner.py:65` and `backend/torob/planner.py:102`; the frontend can only render/recheck the returned `plan.excluded` cards.

`find_offers` returns offers in price order, and `build_plan` slices the first 60 excluded offers before the UI prioritizes observed sellers. If 60 cheaper offers fail another hard condition and a more expensive eligible primary later receives `no_response`, its observed offer is outside that slice. The result contains no primary/fallback and omits the just-unanswered seller from every visible recheck action. Sorting observed sellers in the browser cannot recover an offer omitted by the API.

**Reproduced:** `/tmp/torob-review-repro.py`, `recheck_hidden` case, uses imported source-shaped records with 60 cheaper shops outside the radius and one eligible shop inside it. Before the report, primary is `reachable`. After confirming `no_response`, the result is `primary=null`, `excluded_offers=61`, `len(excluded)=60`, and `reported_offer_returned=false`. The supplied real catalogue has **12 products with more than 60 offers**, with a maximum of **105**, so this is within its supported scale.

**Impact:** The central T4 exhausted-alternatives flow loses its promised explicit recheck action. A buyer cannot record the later available reply through the interface while preserving the same mission.

**Fix direction:** Prioritize offers with active observations before applying the response bound, or expose a bounded/paginated recheck collection that always retains the relevant reported seller. Apply the policy in both empty and nonempty-plan branches; test a primary beyond the first 60 cheaper exclusions.

### 3. The 24-hour purge leaves a permanent duplicate of raw model requests/results

**Location:** `backend/torob/model_jobs.py:58–59`, `backend/torob/agent.py:207–218` and the persisted turn context/result.

The retention cleanup clears `model_jobs.payload` and `model_jobs.result`, but `AgentService` independently persists the original user message in `turns.data.message` and copies model result/context into that same JSON document. Neither expiry nor startup removes/redacts these turn records. The request/result purge therefore does not fulfill the model-runtime plan's M2 requirement to purge raw input/output after 24 hours. Expiring the session prevents subsequent session use but does not remove its raw input from the persistent application database.

**Reproduced:** `/tmp/torob-review-repro.py`, `retention` case, completes a turn containing `REVIEW_PRIVATE_REQUEST_MARKER`, advances beyond 24 hours and invokes the implemented queue expiry. Output is `job_payload="{}"`, `job_result=null`, but `raw_message_still_in_turns=true`.

**Impact:** User-entered needs and pasted seller replies remain on persistent disk indefinitely despite the specified bounded retention behavior. This is an actual retained duplicate, not a hypothetical leak.

**Fix direction:** Apply the retention policy to the owning application's stored turn request/result copies as well as queue rows, preserving only allowed timing/state/evidence metadata. Filter/redact history reads consistently and run cleanup at startup and during ordinary service activity. Keep confirmed domain observation history treatment explicit, since that is a separate append-only record requirement.

### Minor

None reported; no style-only findings added.

## Recommendations

Add one focused regression for each reproduced behavior before the executor's fix pass. For the restore race, exercise both late success and failure because both paths affect the current saved mission. For the excluded-offer case, verify the reported seller is actually reachable through the UI response, rather than only asserting backend eligibility. For retention, inspect all application copies, not only the queue row.

Rebuild the frontend and private delivery artifact after any accepted implementation changes; existing container/artifact results describe the pre-fix source. Do not treat this review or the green unit suite as hosted verification.

## Declined to judge

- Actual Liara provisioning, disk mounting, HTTPS cookies and hosted worker roundtrips: no resource has been provisioned, and the explicitly required concrete approval is pending. Local container evidence does not establish these results.
- The separately running complete 23-row rendered UI acceptance ledger and real mobile-app launch behavior: this review performed its own controlled browser regression and source inspection but does not replace or pre-approve those independent acceptance results.
- Real seller stock/contact accuracy or financing/ride fulfillment: the supplied contacts are synthetic and external handoffs deliberately make no such claim; no seller interaction or transaction was attempted.

## Assessment

**Ready to merge: With fixes.** The local design has strong deterministic and isolation boundaries, but the three reproduced gaps should be resolved before the local implementation is treated as finished. Independent UI acceptance and all actual hosted/publication acceptance remain open unless their own final evidence is recorded; this review does not close them.
