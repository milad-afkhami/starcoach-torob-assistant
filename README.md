# Torob — Plan B before you leave

A Persian in-person shopping assistant for the Starcoach2026 challenge. It prepares an exact-product purchase plan and a nearby alternative, then repairs the plan when a seller's price or availability changes while preserving the buyer's constraints.

**Build in progress.** The model runtime is the first phase; the shopping app and deployment are not complete. Current state: [kanban](docs/insured-vibe-coding/kanban.md). Decisions and measured evidence: [implementation progress](docs/implementation-progress.md).

## Development

Requirements: Python3.12 and uv; Node/npm for the upcoming interface; Docker and local Codex authentication for real model calls.

```bash
uv sync
uv run pytest -q
uv run ruff check backend tests scripts
```

The outbound model worker and private configuration are described in [model-runtime.md](docs/model-runtime.md). No credential, complete catalogue archive or generated database belongs in this repository.

## Data honesty

The mandatory challenge dataset contains synthetic phone numbers and mostly anonymized shops. Recorded prices/hours are historical statements, not current stock or independently confirmed opening. The product will distinguish dataset evidence, user-reported replies and explicitly labelled simulations. It never contacts synthetic phone numbers or silently changes the selected product/budget/visit requirements.
