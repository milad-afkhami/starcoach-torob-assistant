# QA plan — conversation-first Torob

App: isolated deterministic fixture worker at http://127.0.0.1:8684 (online fixture) and :8685 (actual no-worker app). Actual catalogue/API/browser; no genuine model calls. This changes the principal UI and owes real rendered QA. Independent omission review and desktop/mobile rendered acceptance were completed by the read-only usability reviewer; evidence is in `docs/qa-evidence/conversation/`.

| # | Scenario | Steps | Expected result | Status |
|---|---|---|---|---|
| C1 | First-time comprehension | Open desktop and mobile | One welcoming question and bottom composer, no empty results/sidebar | ✅ independent desktop/mobile empty screenshots; conversation.spec mobile welcome |
| C2 | Grounded response | Type request and send | User message, assistant prose, source products and next step in one timeline | ✅ conversation.spec welcome/timeline; max six source cards |
| C3 | Continuation persistence | Send ordinal comparison | Earlier reply remains; new user/assistant pair and exact ordered inline comparison | ✅ conversation.spec timeline plus discovery-context.spec exact ordinal comparison |
| C4 | Purchase plan | Choose product or sample | Text then plan/seller cards/map then next step; historical/synthetic disclosure visible | ✅ independent-flow-results.json desktop/mobile; shopping.spec exact recovery |
| C5 | Real map | Inspect and keyboard-select marker/list | Source coordinates, primary/backup distinction, equivalent selection, zoom/pan, attribution | ✅ conversation.spec marker/list keyboard; independent-flow-results.json actual coordinates/destinations |
| C6 | Basemap failure | Block tile requests | Clear failure, source markers/address list remain useful | ✅ conversation.spec blocked tiles; independent mobile tileFailure=1 |
| C7 | Recovery | Preview unavailable then confirm | No change before confirmation; delta and new same-product plan appear chronologically | ✅ shopping.spec recovery + independent before/preview/after/delta/destination |
| C8 | Conditions | Edit budget/radius and approve | Explicit application with revision guard; old plan remains read-only | ✅ purchase-completion.spec budget/radius/stale revision acceptance |
| C9 | Deterministic fallback | Worker unavailable/manual search | Search/filter access and clear unavailable state; no fake AI response | ✅ offline-isolation.json actual no-worker app; manual search20 products and selection |
| C10 | Cancel/races | Run existing cancellation/replacement/polling cases | Late responses cannot modify newer state or attach old context | ✅ discovery-context/polling-recovery/shopping race cases in browser-results.json |
| C11 | Mobile and keyboard | 390px and keyboard controls | Reachable composer, readable cards, no page overflow, focus visible | ✅ Enter/Shift+Enter/controlled IME event, mobile overflow, dialog focus cases |
| C12 | Browser runtime | Primary journeys | No application console errors; external tile failures disclosed | ✅ independent-flow-results.json and screenshot runtime.json application_errors=[] |

| # | Scenario | Steps | Expected result | Status |
|---|---|---|---|---|
| C13 | Fresh conversation | Reset after plan/transport; reset pending initial turn | Drafts, dialogs, proposals and parent references clear; late result ignored | ✅ conversation.spec + independent reset evidence |
| C14 | Reload honesty | Reload selected plan | Owned mission returns; explicit previous-messages-not-restored text; no stale proposal | ✅ conversation.spec reload |
| C15 | Ordinary help/no-match | Ask no-match then help in actual fixture pipeline | Source-backed empty/clarification responses stay in timeline and allow next message | ✅ conversation.spec assistant no-match/help |
| C16 | Message while plan visible | Ask about current selected product | Current constraints stay unchanged until explicit action | ✅ conversation.spec current-plan continuation |
| C17 | Owner isolation | Two independent browser contexts on no-worker app | Second owner has no messages and GET foreign mission returns404 | ✅ offline-isolation.json |
| C18 | Bottom reachability | Scroll response end desktop/mobile | Closing text/actions above composer | ✅ conversation.spec geometry + independent-flow-results.json |

Result:18/18 rows verified. Stable canonical browser run50/50;22 frontend logic checks;256 unchanged backend checks at first runnable milestone; Ruff/TypeScript/Vite/whitespace pass. This is deterministic fixture-worker/local rendered acceptance, not a genuine model or hosted acceptance claim. IME coverage uses a controlled composing-key event against the actual rendered textarea; no OS input-method automation is claimed.

Failure inventory is preserved under `docs/qa-evidence/conversation-red/`: initial missing chat/map; first broad37/41 (obsolete positional assertion, missing sample source checkbox and renamed origin hook); second46/47 (keyboard send before capability readiness); marker keyboard2/3 (real accessibility defect fixed); third47/50 (shared test owner correctly hit its ten-request ceiling and one old test loaded before density update). Tests now use three independent suite users without changing any limiter, model budget or stored quota. A separate offline QA driver initially lacked its base URL; that harness failure was fixed before its successful recorded run. Raw traces/screenshots remain under `/tmp/starcoach-ui-revision-20261023/torob-*-failure*` and `torob-*-inventory`; no failed attempt is reclassified as a pass.
