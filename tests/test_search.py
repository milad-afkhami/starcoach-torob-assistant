import pytest
from catalogue_fixtures import archive, records


def catalogue(tmp_path, rows=None):
    from torob.ingest import ingest_archive
    from torob.catalogue import Catalogue

    path = tmp_path / "catalogue.sqlite"
    ingest_archive(archive(tmp_path, rows), path, expected_hashes={})
    return Catalogue(path)


def constraints(**kw):
    from torob.types import SearchConstraints

    return SearchConstraints(lat=35.7, lon=51.4, visit_at="2026-10-22T20:15:00+03:30", **kw)


def test_search_normalization_and_category(tmp_path):
    c = catalogue(tmp_path)
    assert [
        p.product_id for p in c.search_products(constraints(query="گوشی 128", category="گوشی موبایل"))
    ] == ["p1"]
    assert [p.product_id for p in c.search_products(constraints(query="A07"))][0] == "p1"
    assert c.search_products(constraints(query="A07", category="لپ تاپ")) == []
    assert c.search_products(constraints(query="A07", max_price_toman="99")) == []


@pytest.mark.parametrize("query", ['" OR *', "NEAR(a,b)", 'foo"; DROP TABLE offers; --', "", "   "])
def test_fts_input_is_literal_not_query_code(tmp_path, query):
    c = catalogue(tmp_path)
    assert isinstance(c.search_products(constraints(query=query)), list)
    assert len(c.find_offers("p1", constraints())) == 3


def test_offer_money_dates_distance_and_source_uncertainty(tmp_path):
    c = catalogue(tmp_path)
    offers = c.find_offers("p1", constraints())
    assert offers[0].price_toman == "100" and offers[0].stock_state == "unknown"
    assert offers[0].hours_state == "open" and 0 < offers[0].straight_line_km < 0.02
    assert offers[0].price_changed_at.startswith("2026-10-12")
    assert offers[0].contact_links == []
    assert "phone" not in offers[0].model_dump_json()


def test_flagged_and_missing_prices_cannot_qualify_as_budget(tmp_path):
    rows = records()
    rows["offers.csv"][0]["price_toman"] = None
    rows["offers.csv"][1]["price_toman"] = 499258940504558912
    c = catalogue(tmp_path, rows)
    offers = c.find_offers("p1", constraints(max_price_toman="500"))
    assert {o.price_quality for o in offers} == {"normal", "missing", "flagged"}
    assert next(o for o in offers if o.offer_id == "o2").price_toman == "499258940504558912"


def test_search_constraints_reject_unsafe_units_coordinates_and_time():
    from torob.types import SearchConstraints
    from pydantic import ValidationError

    for kw in [
        {"lat": float("nan")},
        {"lat": 100},
        {"lon": 190},
        {"radius_km": -1},
        {"max_price_toman": "-1"},
        {"max_price_toman": 100},
        {"visit_at": "2026-10-22T20:00:00"},
    ]:
        with pytest.raises(ValidationError):
            SearchConstraints(**kw)


def test_product_price_cites_the_offer_not_only_product(tmp_path):
    c = catalogue(tmp_path)
    hit = c.get_product("p1")
    assert hit.min_recorded_price == "100" and "o1" in hit.evidence_ids
    assert "o1" in c.search_products(constraints(query="A07"))[0].evidence_ids


def test_budget_filter_precedes_retrieval_limit(tmp_path):
    rows = records()
    base_product = rows["products.csv"][0]
    base_offer = rows["offers.csv"][0]
    rows["products.csv"] = [{**base_product, "product_id": f"p{n:03d}"} for n in range(101)] + [
        {**base_product, "product_id": "zz-affordable"}
    ]
    rows["offers.csv"] = [
        {
            **base_offer,
            "product_id": p["product_id"],
            "offer_id": f"o{n}",
            "price_toman": 50 if p["product_id"] == "zz-affordable" else 1000,
        }
        for n, p in enumerate(rows["products.csv"])
    ]
    c = catalogue(tmp_path, rows)
    assert [p.product_id for p in c.search_products(constraints(query="A07", max_price_toman="100"))] == [
        "zz-affordable"
    ]
