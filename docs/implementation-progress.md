# Implementation progress and rulings

## Current mandate

Implement Torob fully, then Liara; move to Liara if Torob has a confirmed external blocker after independent work is exhausted. User explicitly enabled Insured Vibe Coding, Testing Philosophy and Autohelm. OmniRoute is an authorized fallback if Codex performs poorly. Product implementation began22 October2026. No cloud resources or API keys created yet.

## Decisions

- DECISION: use the requested new sibling repository on build/torob; no linked worktree is needed because this is an empty independent repository with no existing branch/work to protect. Alternative: nesting a worktree would obscure the requested product location. Reversible: ordinary branch/worktree creation later.
- Ruling: canonical plans stay in the private planning repository; this repository tracks actual phases/evidence instead of copying the entire private context. The executor ledger lives in .superpowers/sdd/torob-plan; durable evidence/rulings stay here and in the kanban so compaction cannot lose progress.
- Ruling: OmniRoute replaces the former no-alternative-provider restriction only under the user's latest conditional authorization; any actual switch must be explicit in configuration/results, never mislabeled Codex.

## Evidence

- P0: both proposed product paths were absent; Python/uv, Node/npm and Docker are available. No baseline application tests exist.
- Dependencies: M1 produces the ModelRequest/ModelResult/client for T3; M2 job lifecycle feeds session-owned turn state; T1 catalogue feeds T2/planner; T4 overlays never mutate catalogue. No interface conflict found in the final reviewed plan.

## M1 — model client

- RED:20 tests failed for missing runtime implementation. GREEN:26 meaningful scenarios pass, including real subprocess timeout/cancel,100-request shared budget, schema/evidence rejection and credential exclusion. Additional red regression proved NaN/infinite deadlines passed validation; finite-only validation fixes both.
- Actual isolated application call: `docs/qa-evidence/model-smoke.json`, Codex CLI0.163.0 / gpt-6.1-sol,9046ms, valid Persian HOLD. Model-only smoke does not establish shopping intelligence. No OmniRoute switch needed.
- Decision: use the existing pinned official OpenResty image as a neutral container filesystem for the static CLI, overriding its entrypoint; it runs no web server. Alternative: another image download adds no demonstrated benefit. Production configuration requires an explicit image digest.
- No UI surface for this library phase; planned UI QA N/A. Full running-container cancellation verification remains to be recorded alongside worker QA; process cleanup behavior has automated real-process tests.
