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
