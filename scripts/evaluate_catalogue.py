"""Real supplied-catalogue retrieval/plan checks; source facts are not live stock."""

import json
import math
import time
from pathlib import Path
from torob.catalogue import Catalogue, distance_km
from torob.types import Mission, SearchConstraints

c = Catalogue(Path("data/catalogue.sqlite"))
phone = "گوشی موبایل"
queries = [
    ("A07", phone),
    ("سامسونگ", phone),
    ("128", phone),
    ("۱۲۸", phone),
    ("گوشي", phone),
    ("گوشی", phone),
    ("آیفون", phone),
    ("شیائومی", phone),
    ("Nokia", phone),
    ("A16", phone),
    ("لپ تاپ", "لپ تاپ و نوت بوک"),
    ("Lenovo", "لپ تاپ و نوت بوک"),
    ("Asus", "لپ تاپ و نوت بوک"),
    ("دوربین", "لنز دوربین"),
    ("قاب A07", "قاب گوشی"),
    ('" OR *', None),
    ("zzxqvnonexistent", None),
    ("", None),
    ("A07", "لنز دوربین"),
    ("A07", phone),
]
rows = []
latencies = []
for index, (query, category) in enumerate(queries):
    constraints = SearchConstraints(
        query=query, category=category, max_price_toman="1" if index == 19 else None
    )
    c.search_products(constraints)
    elapsed = []
    for _ in range(3):
        start = time.perf_counter()
        hits = c.search_products(constraints)
        elapsed.append((time.perf_counter() - start) * 1000)
    latencies += elapsed
    rows.append(
        {
            "query": query,
            "category": category,
            "budget": constraints.max_price_toman,
            "count": len(hits),
            "ids": [h.product_id for h in hits],
            "warm_ms": elapsed,
        }
    )
    if category:
        assert all(h.category == category for h in hits)
    if index in [16, 17, 18, 19]:
        assert hits == []
assert rows[2]["ids"] == rows[3]["ids"]
assert rows[4]["ids"] == rows[5]["ids"]
fixture_id = "product_adfdc73bc839d15cd7754318"
product = c.get_product(fixture_id)
assert fixture_id in [
    h.product_id for h in c.search_products(SearchConstraints(query=product.title, category=phone))
]
mission = Mission(
    id="demo",
    session_id="local",
    mode="simulation",
    selected_product_id=fixture_id,
    constraints=SearchConstraints(
        lat=35.69508821734553,
        lon=51.41148102579503,
        radius_km=1,
        max_price_toman="40000000",
        visit_at="2026-10-22T20:15:00+03:30",
    ),
)
start = time.perf_counter()
plan = c.plan_mission(mission)
plan_ms = (time.perf_counter() - start) * 1000
assert plan.primary.offer.offer_id == "offer_b08b779f43846d8e8c6aef1d"
assert plan.fallback.offer.offer_id == "offer_dd4dc3e07a9bc3b94af79800"
assert plan.primary.offer.price_toman == "39200000" and plan.fallback.offer.price_toman == "39500000"
separation = (
    distance_km(
        plan.primary.offer.lat, plan.primary.offer.lon, plan.fallback.offer.lat, plan.fallback.offer.lon
    )
    * 1000
)
assert 63 < separation < 64
result = {
    "scenario_count": 20,
    "warm_sample_count": len(latencies),
    "warm_search_p95_ms": sorted(latencies)[math.ceil(0.95 * len(latencies)) - 1],
    "fixture_plan_ms": plan_ms,
    "fixture_separation_m": separation,
    "fixture": plan.model_dump(mode="json"),
    "queries": rows,
    "limitations": "Local warm-cache data tests; historical prices, declared hours, unknown stock. No purchase, seller communication or model intelligence measured.",
}
Path("docs/qa-evidence/catalogue-evaluation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps({k: v for k, v in result.items() if k not in ["fixture", "queries"]}, indent=2))
