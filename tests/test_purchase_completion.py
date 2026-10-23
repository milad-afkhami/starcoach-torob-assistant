"""Same-product recovery suggestions must preserve every unselected hard condition."""
from catalogue_fixtures import records
from test_search import catalogue
from test_planner import mission


def test_minimum_budget_suggestion_is_exact_and_does_not_apply(tmp_path):
    c = catalogue(tmp_path)
    m = mission(max_price_toman="99", radius_km=1)
    plan = c.plan_mission(m)
    proposal = next(p for p in plan.relaxations if p.field == "max_price_toman")
    assert proposal.value == "100" and proposal.delta == "1"
    assert proposal.base_revision == 1 and proposal.eligible_shops == 1
    assert proposal.supporting_offer_ids == ["o1"]
    assert proposal.constraints.max_price_toman == "100"
    assert proposal.constraints.radius_km == 1
    assert m.constraints.max_price_toman == "99" and plan.primary is None
    changed = {key for key in m.constraints.model_dump() if m.constraints.model_dump()[key] != proposal.constraints.model_dump()[key]}
    assert changed == {"max_price_toman"}


def test_minimum_radius_suggestion_is_rounded_up_and_bounded(tmp_path):
    rows = records()
    for s in rows["shops.csv"]:
        s["lon"] = 51.412
    c = catalogue(tmp_path, rows)
    m = mission(max_price_toman="150", radius_km=0.1)
    proposal = next(p for p in c.plan_mission(m).relaxations if p.field == "radius_km")
    assert proposal.value == 1.09 and proposal.delta == "0.99"
    assert proposal.constraints.max_price_toman == "150" and proposal.eligible_shops == 1
    assert c.plan_mission(m.model_copy(update={"constraints": proposal.constraints})).primary.offer.offer_id == "o1"
    for s in rows["shops.csv"]:
        s["lon"] = 52.5
    assert not catalogue(tmp_path, rows).plan_mission(m).relaxations


def test_suggestions_never_bypass_missing_facts_multiple_conflicts_or_reports(tmp_path):
    rows = records()
    rows["shops.csv"][0]["weekly_hours"] = None
    rows["shops.csv"][1]["lon"] = 52
    rows["offers.csv"][2]["price_toman"] = None
    assert not catalogue(tmp_path, rows).plan_mission(mission(max_price_toman="99")).relaxations
    from torob.planner import build_plan
    c = catalogue(tmp_path)
    offers = c.find_offers("p1", mission().constraints)
    for offer in offers:
        offer.observation_reasons = ["reported_unavailable"]
    assert not build_plan(mission(max_price_toman="99"), offers).relaxations


def test_contact_filter_is_real_route_only_and_preserved_in_budget_suggestion(tmp_path):
    rows = records()
    rows["shops.csv"][1]["website_url"] = "https://shop.example/test"
    rows["shops.csv"][2]["website_url"] = "http://127.0.0.1/private"
    c = catalogue(tmp_path, rows)
    p = c.plan_mission(mission(contactable_only=True))
    assert p.primary.offer.shop_id == "s2" and p.fallback is None
    assert {"contact_route_missing"} <= {r for o in p.excluded for r in o.reason_codes}
    p = c.plan_mission(mission(contactable_only=True, max_price_toman="99"))
    assert p.relaxations[0].value == "200" and p.relaxations[0].constraints.contactable_only
    assert p.relaxations[0].supporting_offer_ids == ["o2"]


def test_no_relaxations_when_current_plan_already_has_candidate(tmp_path):
    assert catalogue(tmp_path).plan_mission(mission(max_price_toman="150")).relaxations == []


def test_locations_use_literal_recorded_addresses_without_phone_or_external_geocoder(tmp_path):
    rows = records()
    rows["shops.csv"][0]["address"] = "تهران، جمهوری، پاساژ طبقه دوم"
    rows["shops.csv"][1]["address"] = "تهران، تجریش"
    rows["shops.csv"][2]["address"] = "تهران، جمهوری"
    rows["shops.csv"][2]["lat"] = None
    c = catalogue(tmp_path, rows)
    found = c.search_locations("جمهوری")
    assert len(found) == 1
    assert found[0] == {"shop_id": "s1", "label": "تهران، جمهوری، پاساژ طبقه دوم", "lat": 35.7, "lon": 51.4001, "source": "catalogue_shop_coordinate"}
    assert not c.search_locations("%") and not c.search_locations("__") and not c.search_locations("ج")


def test_search_diagnostics_distinguish_category_budget_and_no_literal_match(tmp_path):
    c = catalogue(tmp_path)
    from test_search import constraints
    category = c.search_diagnostics(constraints(query="A07", category="لپ تاپ"))
    assert category[0]["kind"] == "category" and category[0]["constraints"]["category"] is None
    budget = c.search_diagnostics(constraints(query="A07", category="گوشی موبایل", max_price_toman="99"))
    assert budget[0]["kind"] == "budget" and budget[0]["minimum_toman"] == "100"
    assert budget[0]["constraints"]["max_price_toman"] == "100"
    assert c.search_diagnostics(constraints(query="not-a-recorded-product")) == []
    assert c.search_diagnostics(constraints(query="A07")) == []


def test_comparison_has_same_conditions_local_feasibility_and_missing_specs(tmp_path):
    c = catalogue(tmp_path)
    from test_search import constraints
    compared = c.compare_products(["p1", "p2"], constraints(max_price_toman="150"))
    assert compared[0]["product"]["product_id"] == "p1"
    assert compared[0]["eligible_shops"] == 1 and compared[0]["distinct_shops"] == 3
    assert compared[0]["best_offer"]["price_toman"] == "100"
    assert compared[1]["eligible_shops"] == 0 and compared[1]["best_offer"] is None
    assert compared[1]["product"]["specs"] == []


def test_discovery_contact_filter_and_true_minimum_precede_rank_limit(tmp_path):
    rows = records()
    base_product, base_offer = rows["products.csv"][0], rows["offers.csv"][0]
    rows["shops.csv"][1]["website_url"] = "https://shop.example/"
    rows["products.csv"] = [{**base_product,"product_id":f"p{i:03}"} for i in range(105)]
    rows["offers.csv"] = [{**base_offer,"product_id":p["product_id"],"offer_id":f"o{i}","shop_id":"s2" if i==104 else "s1","price_toman":100 if i==104 else 1000} for i,p in enumerate(rows["products.csv"])]
    c = catalogue(tmp_path,rows)
    from test_search import constraints
    assert [p.product_id for p in c.search_products(constraints(query="A07",contactable_only=True))] == ["p104"]
    d = c.search_diagnostics(constraints(query="A07",max_price_toman="99"))
    assert d[0]["minimum_toman"] == "100"


def test_contact_budget_and_minimum_refer_to_same_offer_not_different_sellers(tmp_path):
    rows = records()
    rows["shops.csv"][1]["website_url"] = "https://shop.example/"
    c = catalogue(tmp_path,rows)
    from test_search import constraints
    request = constraints(query="A07",contactable_only=True,max_price_toman="150")
    assert not c.search_products(request)
    assert c.search_diagnostics(request)[0]["minimum_toman"] == "200"
    assert c.search_products(request.model_copy(update={"max_price_toman":None}))[0].min_recorded_price == "200"


def test_contact_filter_discards_malformed_and_private_urls_without_breaking_search(tmp_path):
    rows = records()
    rows['shops.csv'][0]['website_url']='https://[broken'
    rows['shops.csv'][1]['website_url']='https://localhost/private'
    rows['shops.csv'][2]['website_url']='https://shop.example/'
    c = catalogue(tmp_path,rows)
    from test_search import constraints
    assert c.search_products(constraints(query='A07',contactable_only=True))[0].min_recorded_price == '300'
    assert c.plan_mission(mission(contactable_only=True)).primary.offer.shop_id == 's3'
