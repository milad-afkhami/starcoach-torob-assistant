# QA plan — agent-led Persian purchase workspace

Actual app http://127.0.0.1:8651. User-directed UI revision; no cloud acceptance implied.

| ID | Scenario | Expected result | Status |
|---|---|---|---|
| A1 | Fresh390px mobile viewport | Composer is first useful input, manual search discoverable, no overflow | ✅ 13-browser suite: composer in390px viewport before manual search; independent revised judge confirms no overflow. |
| A2 | Desktop1440px | Same responsive workflow, mission readable without trapped nested scrolling | ✅ Independent1440/390px review and docs/images/overview.png: shared responsive flow, no trapped notebook scroll. |
| A3 | Focus search field by keyboard/pointer | One coherent composite focus state, no child double outline | ✅ Actual browser regression checks child outline none and visible composite shadow. |
| A4 | Select pointer/keyboard/Escape/outside/disabled | Accessible, controlled value, focus return and dismissal | ✅ Actual pointer/keyboard regression; initial modal Escape/label-activation defects reproduced then fixed. |
| A5 | Compare products with keyboard | Custom-styled checkbox retains semantics/focus | ✅ Actual keyboard Space/checked/focus and designed checkbox appearance regression. |
| A6 | Genuine Persian needs request | User turn, supported assistant text/cards, explicit proposal; no invented facts | ✅ Independent final one-call request:40M/1km/today→proposal45M/5km/tomorrow11; exact confirmed match8shops,18.4s. |
| A7 | Cancel/error/offline | Honest status, no false completed assistant response; manual search usable | ✅ Independent review observed real worker-offline manual search; restored capabilities true. Delayed transport cancel/stale response assertions pass in current actual browser suite; prior genuine runtime cancellation evidence remains separately recorded. |
| A8 | Full sample and budget/no-response recovery | Original protected mission behavior passes | ✅ Actual current recovery/no-response/reload/budget regressions and independent source-row seller swap pass; final independent grouped-list check confirms nonreported groups collapsed and reported sellers recheckable. |
| A9 | Persian glyphs and technical identifiers | ss01 active on prose/inputs; machine data/identifiers deliberately isolated | ✅ fontTools confirms ss01; actual body computed ss01; exact BigInt/Persian-input tests unchanged and green; technical LTR styles isolated. |
| A10 | Blind follow-up judgment | Fresh source/output review, unresolved deductions retained | ✅ Independent blinded source/output rejudge214→235/300, with cloud and remaining product deductions retained. |

Evidence: frontend/test-results/results.json (latest serial13-browser run), docs/qa-evidence/blind-judging.json and independent scratch reports. No hosted acceptance claim.
