# QA plan — full CSV source package

This phase changes private packaging and the Docker catalogue build stage; it does not change UI or application/domain behavior. No new rendered UI pass is owed; canonical affected import/packaging checks, full backend and real constrained image/API acceptance are required. The original uncertain XZ upload remains untouched and unreleased. Root owns deployment-artifact.json; do not stage or overwrite it.

Plan: preserve default XZ packaging; add explicit original-ZIP packaging with validated source/payload hashes and fixed allowlisted private members; build the complete catalogue in an alternate Docker build stage, retaining the same runtime/security/entrypoint. Add canonical semantic comparison tooling/evidence excluding only measured import duration, then run the new source package through the actual legacy Docker builder and constrained runtime acceptance.

| # | Scenario | Required evidence | Status |
|---|---|---|---|
| P1 | Explicit ZIP mode contains complete hash-validated source, backend and frozen UI only | Red/green packaging tests, real tar members/hash/size; no credentials/state/XZ/public ZIP | ✅ artifact-inspection.json; full original ZIP, all members/hash/size verified |
| P2 | Bad/missing/unsafe/symlink source or runtime input fails without output | Import/packaging negative regressions; old artifact preserved | ✅ 35 packaging tests, independent review reds and no-follow/alias/race/collision regressions; negative-results.json |
| P3 | Existing XZ mode remains reproducible | Existing package/unpack tests | ✅ default XZ package/cache/unpack regressions pass |
| P4 | Real legacy build from private new archive | Completed DOCKER_BUILDKIT=0 build and generated DB hash | ✅ 22/22 actual legacy build; build.json and legacy-build.txt |
| P5 | Every row/field/schema/index/source digest equals the current catalogue | Ordered all-column digests of shops/products/offers/FTS; metadata excluding duration only | ✅ semantic-equivalence.json compares every row/column and schema/index/source metadata; new DB SHA separately retained |
| P6 |512MiB/.5CPU actual image, named volume and root-owned bind | PID1 UID/GID10001/no caps/no-new-privileges, exact fixture/recovery, frozen assets, full counts, private404 and restart persistence | ✅ container-named.json + container-root-bind.json; both actual constrained runs and frozen assets/private404/restart |
| P7 | Canonical source acceptance | Full backend, Ruff, whitespace; unchanged frontend evidence retained | ✅ 296 backend pass;44 targeted pass; Ruff/whitespace pass; unchanged UI evidence retained |

Any failure remains in the evidence ledger. No upload, provider write, genuine model call, live restart or registry publication is part of this phase.

Result:7/7 rows verified. Independent review reproduced a predictable-temp symlink overwrite, source/output alias overwrite and input path race; all were corrected together using held no-follow regular-file descriptors, parent/inode/content snapshots, exclusive random0600temporary files, output/report alias guards and dir-fd publication. Existing size-limit tests also caught an intermediate buffered-size mistake; it was fixed before the final296-test suite. The final archive has the same individual member hashes as the actual successful image-build input, so build/semantic/constrained evidence is reused without another identical build. Source code and artifact are ready for root publication/deployment; no upload/provider acceptance is claimed.
