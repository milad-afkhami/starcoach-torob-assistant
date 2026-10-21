from catalogue_fixtures import records
from test_search import catalogue, constraints


def mission(**kw):
    from torob.types import Mission

    return Mission(id="m1", session_id="s1", selected_product_id="p1", constraints=constraints(**kw))


def test_primary_and_distinct_nearby_backup(tmp_path):
    c = catalogue(tmp_path)
    plan = c.plan_mission(mission(max_price_toman="250"))
    assert plan.primary.offer.offer_id == "o1" and plan.fallback.offer.offer_id == "o2"
    assert plan.primary.offer.shop_id != plan.fallback.offer.shop_id
    assert all(o.offer.product_id == "p1" for o in plan.choices)


def test_declared_closed_cheapest_is_excluded(tmp_path):
    rows = records()
    rows["shops.csv"][0]["weekly_hours"]["thu"]["shifts"][0]["end_time"] = "18:30:00"
    plan = catalogue(tmp_path, rows).plan_mission(mission())
    assert plan.primary.offer.offer_id == "o2" and plan.fallback.offer.offer_id == "o3"
    assert any("closed_at_visit" in x.reason_codes for x in plan.excluded)


def test_duplicate_offer_not_backup(tmp_path):
    rows = records()
    rows["offers.csv"].append({**rows["offers.csv"][0], "offer_id": "o4", "price_toman": 101})
    plan = catalogue(tmp_path, rows).plan_mission(mission())
    assert plan.fallback.offer.shop_id == "s2"
    assert plan.shortlist_coverage["distinct_shops"] == 3


def test_missing_payment_channel_is_not_eligibility(tmp_path):
    rows = records()
    rows["shops.csv"][0]["payment_options"] = [
        {
            "provider_name": "ترب‌پی",
            "channel": "unknown",
            "category_names": [],
            "min_price_toman": None,
            "max_price_toman": None,
        }
    ]
    plan = catalogue(tmp_path, rows).plan_mission(mission(payment_provider="ترب‌پی"))
    assert plan.primary is None and plan.fallback is None
    assert any(x.eligibility == "needs_verification" for x in plan.excluded)


def test_payment_known_channel_category_and_amount(tmp_path):
    rows = records()
    rows["shops.csv"][0]["payment_options"] = [
        {
            "provider_name": "ترب‌پی",
            "channel": "in_person",
            "category_names": ["گوشی موبایل"],
            "min_price_toman": 50,
            "max_price_toman": 150,
        }
    ]
    plan = catalogue(tmp_path, rows).plan_mission(mission(payment_provider="ترب‌پی"))
    assert plan.primary.offer.shop_id == "s1" and plan.fallback is None
    rows["shops.csv"][0]["payment_options"][0]["max_price_toman"] = 99
    assert catalogue(tmp_path, rows).plan_mission(mission(payment_provider="ترب‌پی")).primary is None


def test_missing_hours_price_and_outside_radius_are_explicit(tmp_path):
    rows = records()
    rows["shops.csv"][0]["weekly_hours"] = None
    rows["offers.csv"][1]["price_toman"] = None
    rows["shops.csv"][2]["lat"] = 36
    plan = catalogue(tmp_path, rows).plan_mission(mission())
    assert plan.primary is None and plan.fallback is None
    reasons = {r for option in plan.excluded for r in option.reason_codes}
    assert {"hours_unknown", "price_missing", "outside_radius"} <= reasons


def test_no_nearby_fallback_is_not_invented(tmp_path):
    rows = records()
    rows["shops.csv"][1]["lon"] = 51.42
    rows["shops.csv"][2]["lon"] = 51.43
    plan = catalogue(tmp_path, rows).plan_mission(mission(radius_km=5))
    assert plan.primary.offer.shop_id == "s1" and plan.fallback is None


def test_explicit_choice_must_be_eligible(tmp_path):

    c = catalogue(tmp_path)
    m = mission(max_price_toman="250").model_copy(update={"selected_primary_shop_id": "s3"})
    assert c.plan_mission(m).primary.offer.shop_id == "s1"
    m = m.model_copy(update={"selected_primary_shop_id": "s2"})
    assert c.plan_mission(m).primary.offer.shop_id == "s2"
