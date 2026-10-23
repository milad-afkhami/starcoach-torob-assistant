# QA plan — pinned organizer download during build

Explicit new source/build design after two uncertain large transfers; no upload, provider write or real model call in this phase. Existing application/UI and ZIP/XZ modes stay unchanged. Only the Docker build stage may download the single pinned HTTPS organizer archive; runtime never downloads/rebuilds data. Local actual download/build, full semantic/schema/index/payload/count equivalence with truthful ZIP-envelope provenance, source privacy, affected negative tests and canonical backend are required. Prior container security/persistence evidence is reused only if actual runtime input equivalence is established; otherwise run affected constrained acceptance.

| Gate | Expected | Status |
|---|---|---|
| R1 | Fixed URL/SHA/size, default TLS, no auth/cookies/proxies/redirects, bounded streaming and atomic safe outputs; negative regressions | ✅ 7downloader transfer/header/redirect/hash/length/symlink tests; TLS/no-proxy default opener; existing safe writer regressions |
| R2 | Small allowlisted package excludes ZIP/DB/state/credentials; remote mode explicit, old modes retained | ✅ remote package test + actual artifact-inspection.json;315502bytes; no ZIP/SQLite/XZ/state/credentials |
| R3 | Actual legacy Docker build downloads the real pinned organizer bytes and imports the full catalogue | ✅ actual22-step legacy build, uncached real download then complete import; build.json + legacy-build.txt |
| R4 | Every row/field/FTS/schema/index and source payload hash/count matches; raw archive provenance difference checked explicitly | ✅ semantic-equivalence.json; exact checked37a→b0afarchive pair, all other metadata and rows/FTS/schema/index/payloads/counts equal |
| R5 | Final runtime/data/privacy/frozen UI and constrained acceptance established | ✅ new image actual512MiB/.5CPU named/root-bind nonroot/caps/private404/restart/frozen-UI/source fixture/recovery; runtime data onlycatalogue.sqlite |
| R6 | Canonical backend/Ruff/whitespace; old unknown uploads untouched, root deployment record preserved | ✅ 305backend/53affected/Ruff/whitespace pass; no provider or model actions |

Result:6/6 local gates pass. Actual build246.658seconds including the real pinned organizer download and64.878-second import; no actual transfer/build failure. Final image was exercised directly for both storage routes, so prior container acceptance was not substituted for the changed database provenance. Unknown large uploads are retained by root; no upload/release is part of this evidence. Provider builder CDN access and hosted acceptance remain separate root delivery obligations.
