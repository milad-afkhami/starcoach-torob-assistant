# QA plan — owned-turn polling transport recovery

The controlled cases were written in `frontend/e2e/polling-recovery.spec.ts` before the rendered red run. They replace only turn transport responses, use the real application/sample interface, and never call a model. The original failure reproduces a missing typed observation preview after one lost polling response.

| Case | Boundary | Required result |
|---|---|---|
| P1 | One dropped GET followed by the same completed reply | Exactly one turn POST, two reads of the same ID, original typed preview rendered, no confirmation or plan change |
| P2 | Persistent read transport failure | Initial read plus at most three shared retries, then explicit error; no new turn or continued reads |
| P3 | User cancellation during retry backoff | Cancel the existing turn; no second read, preview or stale discovery parent |
| P4 | Turn-creation POST transport failure | Single POST attempt, no polling or implicit replay |

Unit checks additionally exercise one shared retry budget across successive polls, original monotonic deadline before/after waits and completed reads, explicit exclusion of401/403/404/409/429/500/501, and bounded502/503/504 recovery. A native hanging-fetch test also checks actual AbortSignal behavior. The GET is aborted when its remaining original deadline expires, and that event latches terminal expiration so sub-millisecond timer rounding cannot issue an extra read. There is no new inference, deadline extension, quota reset or automatic confirmation.

[Measured results and hashes](../../qa-evidence/polling-recovery.json) own final execution evidence. Backend256-test evidence remains valid only while its source hash is unchanged.
