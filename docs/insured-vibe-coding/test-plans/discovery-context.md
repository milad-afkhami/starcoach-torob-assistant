# QA plan — bounded discovery continuation

Use the isolated real application with `tests/discovery_fixture_server.py` on127.0.0.1:8672 and the complete imported catalogue. Its worker is a deterministic protocol fixture, makes no model calls and never uses personal/provider credentials. This verifies actual HTTP/session/rendering behavior, not Persian model quality. Browser scenarios were first codified in `frontend/e2e/discovery-context.spec.ts` before their red runs; this table records the final acceptance scope.

| Case | Scenario | Expected | Status |
|---|---|---|---|
| D1 | First discovery, then “compare second with first” | Second request carries the exact owned parent; comparison shows the prior displayed second/first titles, not recommendation order or new search matches | ✅ |
| D2 | Ambiguous “same model, more memory” | Clarify RAM/internal storage, retain exact source cards, never mutate an existing mission or infer a capacity | ✅ |
| D3 | Manual search replaces discovery | Clear parent; a later ordinal asks for grounded options instead of guessing | ✅ |
| D4 | Sample replaces discovery | Clear parent and leave its exact selected variant in the mission | ✅ |
| D5 | A completed discovery response arrives during delayed sample loading | Clear the old parent at actual card replacement; sample cards cannot inherit an unrelated discovery reference | ✅ |
| D6 | Session/TTL/type failures | Cross-owner, expired, failed, canceled, reply, mission-bound and empty parents denied before model enqueue; optional field preserves ordinary clients | ✅ |
| D7 | Invalid model references | Unknown/duplicate references fail; missing or unavailable word/ASCII/Persian/Arabic numeric ordinals and unbound same-model hints clarify rather than start guessed text searches | ✅ |
| D8 | All contextual clarification exits | Generic model clarification, memory ambiguity, invalid resolution, incomplete comparison, missing family identity and no hits retain all eight source cards and their original filtered prices/offer evidence, independently of the six-card prompt bound | ✅ |
| D10 | Exact-reference comparison in both orders | Preserve original filtered price/offer evidence and current contactability constraints; global comparison facts remain a separate API scope | ✅ |
| D9 | Accepted diagnostic during held old AI completion | New manual source results persist, old completion cannot overwrite or attach its parent, actual cancel request emitted | ✅ |

D1–D5 and D9 require actual rendered evidence; D6–D8 are enforced by HTTP/domain tests. Genuine live-model and hosted acceptance remain root-owned separate gates.

Final evidence: [discovery-context.json](../../qa-evidence/discovery-context.json). Genuine model/hosted follow-up remains a separate acceptance gate.
