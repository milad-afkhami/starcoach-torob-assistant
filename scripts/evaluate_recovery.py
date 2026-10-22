"""Repeatable, deliberately adversarial fixtures—not a purchase-success estimate."""

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from torob.planner import build_plan
from torob.types import Mission, OfferHit, SearchConstraints


def offer(index):
    return OfferHit(
        offer_id=f"o{index}",
        product_id="p1",
        shop_id=f"s{index}",
        shop_name=f"Fixture {index}",
        identity_anonymized=True,
        address="Synthetic evaluation address",
        lat=35.7,
        lon=51.4 + index / 10000,
        price_toman=str(index * 100),
        recorded_price_toman=str(index * 100),
        price_quality="normal",
        price_changed_at="2026-10-12T00:00:00Z",
        straight_line_km=index / 100,
        hours_state="open",
        weekly_hours=None,
        payment_state="supported",
        payment_evidence=[],
        evidence_ids=[f"offer:o{index}"],
        contact_links=[],
        seller_title="Fixture exact model",
        warranty=None,
    )


def evaluate_synthetic():
    cases = []
    names = [
        "unavailable",
        "no_response",
        "price_increase",
        "wrong_variant",
        "payment_conflict",
        "closed_at_visit",
        "unknown_hours",
        "exhausted",
    ]
    for name in names:
        mission = Mission(
            id="fixture",
            session_id="evaluation",
            mode="simulation",
            selected_product_id="p1",
            constraints=SearchConstraints(
                max_price_toman="300",
                lat=35.7,
                lon=51.4,
                payment_provider="ترب‌پی",
                visit_at="2026-10-22T20:15:00+03:30",
            ),
        )
        before = [offer(i) for i in range(1, 4)]
        if name == "closed_at_visit":
            before[0].hours_state = "closed"
        if name == "unknown_hours":
            before[0].hours_state = "unknown"
        frozen = build_plan(mission, before)
        after = [o.model_copy(deep=True) for o in before]
        reasons = {
            "unavailable": "reported_unavailable",
            "no_response": "no_response",
            "wrong_variant": "variant_mismatch",
            "payment_conflict": "reported_payment_conflict",
        }
        if name in reasons:
            after[0].observation_reasons = [reasons[name]]
        if name == "price_increase":
            after[0].price_toman = "350"
        if name == "exhausted":
            for o in after:
                o.observation_reasons = ["no_response"]
        if name not in ("closed_at_visit", "unknown_hours"):
            for o in after:
                if o.observation_reasons or o.price_toman != o.recorded_price_toman:
                    o.observation_provenance = "simulation"
        expected = None if name == "exhausted" else "o2"
        original = mission.model_dump(mode="json")
        samples = []
        for _ in range(30):
            start = time.perf_counter()
            plan = build_plan(mission, after)
            samples.append((time.perf_counter() - start) * 1000)
        chosen = plan.primary.offer.offer_id if plan.primary else None
        old = frozen.primary.offer.offer_id if frozen.primary else None

        def score(value):
            return {"selected_offer": value, "correct": value == expected}

        cases.append(
            {
                "case": name,
                "expected": expected,
                "static_price": score("o1"),
                "static_eligible": score(old),
                "plan_b": score(chosen),
                "unchanged_constraints": mission.model_dump(mode="json") == original,
                "all_stock_unknown": all(o.stock_state == "unknown" for o in after),
                "latency_ms": {"median": statistics.median(samples), "p95": sorted(samples)[28]},
                "protocol": {
                    "preview_and_confirm_actions_per_event": 2,
                    "repeated_requirement_entry": 0,
                    "measured_human_actions": False,
                },
            }
        )
    return {
        "scope": "Eight synthetic adversarial cases; not random sampling or live seller outcomes.",
        "baselines": "Price-first ignores eligibility. Static-eligible selects once using initial facts; neither baseline processes later replies. Both receive identical initial catalogue and constraints.",
        "oracle": "Expected o2 for seven cases, no match when all three shops are unanswered; specified independently of planner output.",
        "cases": cases,
    }


def evaluate_real(path):
    from torob.catalogue import Catalogue, distance_km
    from torob.session import Store

    catalogue = Catalogue(path)
    with tempfile.TemporaryDirectory(prefix="torob-recovery-") as directory:
        store = Store(Path(directory) / "state.sqlite", "evaluation-secret-not-a-runtime-key-32", catalogue)
        _, owner = store.create_session(100)
        mission = store.create_mission(
            owner,
            "product_adfdc73bc839d15cd7754318",
            SearchConstraints(
                lat=35.69508821734553,
                lon=51.41148102579503,
                radius_km=1,
                max_price_toman="40000000",
                visit_at="2026-10-22T20:15:00+03:30",
            ),
            mode="simulation",
            now=101,
        )
        before = store.plan(owner, mission.id)
        primary, fallback = before.primary.offer, before.fallback.offer
        draft = store.create_followup(owner, mission.id, primary.offer_id, 102)
        preview = store.preview_observation(
            owner, mission.id, draft["id"], 1, "unavailable", raw_text="شبیه‌سازی ناموجود", now=103
        )
        start = time.perf_counter()
        after, delta = store.confirm_observation(owner, mission.id, preview["id"], 1, 104)
        elapsed = (time.perf_counter() - start) * 1000
        assert primary.price_toman == "39200000" and fallback.price_toman == "39500000"
        assert after.primary.offer.offer_id == fallback.offer_id and delta.price_delta_toman == "300000"
        assert store.get_mission(owner, mission.id).constraints == mission.constraints
        return {
            "catalogue": str(path),
            "source_product_id": mission.selected_product_id,
            "primary": primary.offer_id,
            "fallback": fallback.offer_id,
            "price_delta_toman": delta.price_delta_toman,
            "straight_line_separation_metres": 1000
            * distance_km(primary.lat, primary.lon, fallback.lat, fallback.lon),
            "confirmation_and_replan_ms": elapsed,
            "provenance": "simulation",
            "fixed_arrival": "2026-10-22T20:15:00+03:30",
            "live_stock_verified": False,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue", type=Path, default=Path("data/catalogue.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("results/recovery.json"))
    args = parser.parse_args()
    result = evaluate_synthetic()
    result["real_catalogue_fixture"] = evaluate_real(args.catalogue)
    result["verified_at_utc"] = (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "cases": len(result["cases"]),
                "plan_b_correct": sum(r["plan_b"]["correct"] for r in result["cases"]),
                "real_fixture": result["real_catalogue_fixture"],
            },
            ensure_ascii=False,
        )
    )
