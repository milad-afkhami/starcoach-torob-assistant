"""Evaluation must score current truth, not reward a frozen unsafe recommendation."""

from pathlib import Path
import importlib.util


def test_evaluation_compares_eight_events_and_fails_unsafe_baselines():
    path = Path(__file__).parents[1] / "scripts/evaluate_recovery.py"
    spec = importlib.util.spec_from_file_location("recovery_eval", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.evaluate_synthetic()
    assert len(result["cases"]) == 8
    assert all(row["plan_b"]["correct"] for row in result["cases"])
    assert sum(row["static_price"]["correct"] for row in result["cases"]) == 0
    assert sum(row["static_eligible"]["correct"] for row in result["cases"]) == 2
    exhausted = next(r for r in result["cases"] if r["case"] == "exhausted")
    assert exhausted["plan_b"]["selected_offer"] is None
    assert all(r["unchanged_constraints"] for r in result["cases"])
