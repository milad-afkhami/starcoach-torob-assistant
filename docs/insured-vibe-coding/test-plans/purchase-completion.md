# QA plan — purchase feasibility and recovery

App under test: isolated local instance using the complete catalogue, separate session DB; root owns main/cloud restart. Existing regression suite remains canonical.

| # | Scenario | Expected result | Status |
|---|---|---|---|
| 1 | Search actual address keyword and select a reference point | Dataset address and exact coordinates populate form, no geocoding claim or mission mutation before explicit Apply | ✅ |
| 2 | Contact-route constraint | Only website/Instagram-linked recorded offers can qualify; synthetic phone never shown; removing restriction is explicit | ✅ |
| 3 | Over-budget empty plan | Minimal single budget increase from normal source price appears, same product and other constraints; no state mutation until acceptance | ✅ |
| 4 | Outside-radius empty plan | Smallest sufficient rounded radius is proposed with straight-line wording; all other conditions remain locked | ✅ |
| 5 | Multi-conflict / reported unavailable / missing facts | No claim that a single change unlocks an unavailable/unknown or multiply conflicting seller | ✅ |
| 6 | Comparison | Same spec keys align across columns; absent facts labelled unknown; local feasibility uses displayed same conditions | ✅ |
| 7 | Empty manual search | Distinguish category mismatch, budget mismatch, and absent literal query; proposed recovery never silently applies | ✅ |
| 8 | Startup transient 429 | Visible Retry restores actual readiness without page reload; success does not discard newer user edits | ✅ |
| 9 | Mobile/keyboard | Reference selector, proposal acceptance, comparison and errors usable at 390px without horizontal page overflow | ✅ |

Independent omission check requested from root before final acceptance. Automated boundary/decision tests are separate evidence; fixture/model simulation is not claimed as real seller confirmation.

Evidence: [purchase-completion.json](../../qa-evidence/purchase-completion.json). Rows3–5 additionally rely on domain decision tests for all safety branches; actual rendered budget/radius/report recovery flows ran against the complete catalogue. HTTP429 is a controlled transport response; successful recovery uses the real application. No genuine seller reply, model call or cloud acceptance is implied.

## Independent review repair acceptance

| # | Scenario | Expected and observed result | Status |
|---|---|---|---|
| 10 | Contact-filtered Samsung comparison | Global prices214,900,000 and134,000,000toman from fresh exact-product records, not filtered309,752,500/150,000,000 values; compatible price separate | ✅ |
| 11 | RAM/storage aliases and unit boundaries | Actual Flip7/A57 RAM aligned in one row with source titles; GB/Persian alias and attached-unit cases pass; GB/MB/type/version unknowns remain separate | ✅ |
| 12 | Comparison HTTP503 | Every derived row says unknown, none claims zero; explicit retry sends identical product/condition body and succeeds | ✅ |
| 13 | Planned visit default and explicit override | Fresh Friday17:00 mission excludes known-closed primary; explicit hours opt-out includes it and remains off after reload | ✅ |
| 14 | Stale proposal after concurrent update | HTTP409 preserves newer21M cap; explicit refresh shows new18.2M increase, does not accept it, and retains unsaved5km draft | ✅ |
| 15 | Readable origin persistence | Selected full dataset address displayed as draft label; mission stays unchanged until Apply, then persists same label/coordinates | ✅ |
| 16 | Pending sample load and fast edit | Controlled delayed source GET reproduces old overwrite; manual fields now disabled while busy, then accept and retain later100toman edit | ✅ |

Final acceptance:206backend,6frontend and26browser tests pass. Browser functional journeys deliberately pace all client API requests under the unchanged180/minute IP limit; this is not a concurrency/load benchmark. Evidence and source hashes are in the linked JSON. Targeted independent re-review remains owned by root.

## Origin-race follow-up

| # | Scenario | Observed result | Status |
|---|---|---|---|
| 17 | Hold a real condition-save response, select Tajrish, then release Republic response | Committed mission remains Republic, newer Tajrish source label/coordinates remain draft, exactly one PATCH; no second automatic write | ✅ |
| 18 | Hold sample product GET, choose Tajrish, then finish building sample | Sample mission remains its declared Republic scenario; newer Tajrish draft survives independently | ✅ |

Both tests failed before the edit-epoch guards and passed after. Full28-browser sweep passed in1.6minutes; five affected flows and five controlled-route pacing cases also pass. No backend change or deployment is part of this follow-up; prior206backend evidence remains separate.
