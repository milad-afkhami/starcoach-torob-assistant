# Architecture and evidence boundaries

The browser renders a Persian RTL purchase workspace. FastAPI serves its compiled assets, public catalogue queries and private mission APIs. A read-only SQLite FTS catalogue contains the complete supplied CSV payloads. A separate persistent SQLite database owns signed-cookie sessions, mission revisions, follow-ups, append-only observations and model jobs. Run exactly one application replica; SQLite and the in-process request limiter are not a multi-replica design.

## Decision flow

An exact search or AI-assisted needs request retrieves source products. The buyer selects one exact product and explicitly sets budget, radius, visit time and payment requirements. Python classifies every offer as candidate, needs verification or ineligible. The shortlist combines up to30 cheapest and30 nearest distinct shops. The primary defaults to cheapest eligible; a fallback must be another eligible shop for the same product within500metres straight-line. UI comparisons also expose source specs, prices, declared hours and missing facts.

A follow-up is an inquiry draft, never an outbound message. Manual outcomes and AI-interpreted replies create stored previews. Confirmation checks the owning session and expected mission revision, applies scoped observations transactionally, and returns the revised plan and exact price delta. No-response remains unknown. A later explicit confirmed reply can supersede it. Rechecks remain reachable even when all original candidates are exhausted. Simulation and assisted missions are separate records; only an owning simulation can reset its observations.

## Model boundary

The application queues bounded JSON requests. A local outbound worker polls the application, runs Codex CLI in an isolated container, and submits typed results using a private bearer token. See [model runtime](model-runtime.md) for limits and isolation. The hosted application never stores Codex authentication. The model cannot execute catalogue SQL, contact sellers, mutate missions or see executor credentials. Retrieved IDs and each cited fact are checked before presentation. Numeric product facts are rendered from catalogue values, not accepted as model-written facts. Proposals require an explicit user action.

Model calls are genuinely useful for Persian need interpretation, retrieved-product explanation and reply interpretation. Search, eligibility, exact money, geometry and recovery work without the model. Cancellation invalidates the browser request generation as well as the server job; a delayed initial response cannot overwrite newer work. The worker is a local availability dependency, not unattended hosted inference. OmniRoute is only a conditionally authorized alternative; this build has not switched providers.

## Storage and deployment

The private image contains the validated catalogue at `/app/data/catalogue.sqlite`; this file is opened read-only/immutable and never served as an HTTP asset. Mount persistent state at `/data/state.sqlite`. `/healthz` checks process liveness; `/readyz` checks the actual catalogue manifest/index availability. HTTPS makes the opaque session cookie Secure; session mutations require the configured exact origin. Browser assets contain no worker/session secrets. The local container was exercised with512MiB/0.5CPU; exact measurements and restart evidence are in [container.json](qa-evidence/container.json). A cloud URL and hosted-worker acceptance remain separate pending gates.

## Limitations

Prices can be stale and stock is unknown. Most shop names and all supplied phone numbers are synthetic. Only provided website/Instagram routes can be handed to the buyer; no synthetic telephone number is actionable. A user-reported reply is not independently verified. No route duration, fare, credit eligibility, authentic-brand guarantee, stock probability or reservation is computed. The catalogue is not live Torob search. External actions open Torob, TorobPay or navigation/ride sites only after a user click; no transaction is performed.

The source dataset has extreme price anomalies, two empty product titles and missing prices/hours/payment evidence. Values remain exact decimal strings; flagged or unknown prices do not qualify as cheap offers. Unknown required facts do not become affirmative eligibility. Minimum-relaxation automation, embeddings, basket planning, live seller automation and payment/ride APIs are out of scope.
