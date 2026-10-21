# QA plan — model runtime

App under test: a real loopback Uvicorn server with the production worker router and persistent SQLite job store; the real outbound worker uses the isolated installed Codex CLI. No UI surface exists yet. The worker/operator flow owes this real HTTP/process pass; TestClient/unit mocks do not close these rows. Initial state is unrun. The harness may seed jobs through the internal queue because user-facing turns arrive in T3.

| # | Scenario | Steps | Expected result | Status |
|---|---|---|---|---|
| 1 | Worker authentication | POST heartbeat without token and with wrong token over HTTP |401; no heartbeat recorded |⬜|
| 2 | Genuine model roundtrip | Seed a bounded schema fixture, run the actual worker |Stored completed Persian JSON, provider/model/latency provenance; no secret in result |⬜|
| 3 | Duplicate result | Repeat completed job's lease/token completion |409; original result unchanged |⬜|
| 4 | Worker disconnect | Stop polling/heartbeat and wait past45 seconds |New inference unavailable; existing result remains readable |⬜|
| 5 | Queue expiry | Enqueue after fresh heartbeat without a worker claim; wait past15 seconds |Expired, no CLI run; reconnect does not execute it |⬜|
| 6 | Cancel running inference | Start worker, observe its actual Docker container, cancel job |Worker cancels/removes container; late completion not accepted |⬜|
| 7 | Persisted state | Reopen queue against same on-disk DB |Completed and canceled job states remain, no replay |⬜|
| 8 | Bounded input | POST over64KiB to worker route |413 without invoking provider |⬜|
| 9 | Malformed input and isolation | Send invalid heartbeat bodies; request leased status as another worker; read/cancel as another owner |422 / 404; original lease unchanged |⬜|
| 10 | Completion credentials and schema validation | Complete a real HTTP lease with wrong lease, wrong token, then schema-invalid output |409 / 409 / 422; no result accepted, invalid output persists failed |⬜|
| 11 | Reconnect recovery | After disconnect and expired backlog, reconnect the actual worker and enqueue a fresh fixture |Expired work stays expired; fresh real model result completes |⬜|
| 12 | Capacity and live process contention | During actual inference attempt another worker and enqueue beyond waiting capacity |Second worker gets busy without claiming; same owner busy; two waiting jobs maximum; only one inference container |⬜|

Coverage pass (before execution): includes authentication as a tested capability, persistence/repetition, disconnect/expiry and cancellation of an actual child container. Public HTTPS hosting and shopping intelligence are explicitly outside this phase and remain T6/T3 gates. Evidence must include HTTP codes, stored rows with secrets removed, timing and container cleanup, not just a generic success screenshot.

Independent coverage review: added rows 9–12 before execution because the original list omitted malformed inputs, isolation, wrong completion credentials, schema-invalid result persistence, reconnect recovery, and contention. These can fail while a happy path still passes. The production queue API is used for setup and owner checks because public turn routes are not implemented yet.
