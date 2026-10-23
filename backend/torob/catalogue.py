import ipaddress
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .hours import hours_state
from .normalize import normalize_text
from .types import OfferHit, ProductHit, SearchConstraints


def distance_km(lat1, lon1, lat2, lon2):
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b - a, math.radians(lon2 - lon1)
    hav = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, hav))))


def _safe_link(value):
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
    except ValueError:
        return None
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
        return None
    if url.hostname.lower() in ("localhost", "localhost.localdomain"):
        return None
    try:
        if not ipaddress.ip_address(url.hostname).is_global:
            return None
    except ValueError:
        pass
    return value


def _contact_sql(alias):
    return f"EXISTS (SELECT 1 FROM shops cshop WHERE cshop.shop_id={alias}.shop_id AND (safe_public_link(json_extract(cshop.data,'$.website_url')) OR safe_public_link(json_extract(cshop.data,'$.instagram'))))"


def payment_state(options, provider, category, price):
    if not provider:
        return "not_required", options or []
    matching = [
        o for o in (options or []) if normalize_text(o.get("provider_name")) == normalize_text(provider)
    ]
    if not matching:
        return "unknown", []
    unknown = False
    for option in matching:
        if option.get("channel") == "unknown" or not option.get("channel"):
            unknown = True
            continue
        if option["channel"] != "in_person":
            continue
        categories = option.get("category_names") or []
        if not categories:
            unknown = True
            continue
        if normalize_text(category) not in {normalize_text(c) for c in categories}:
            continue
        if price is None:
            unknown = True
            continue
        minimum, maximum = option.get("min_price_toman"), option.get("max_price_toman")
        if minimum is not None and price < int(minimum):
            continue
        if maximum is not None and price > int(maximum):
            continue
        return "supported", matching
    return ("unknown" if unknown else "unsupported"), matching


def rank_by_price(offers):
    return sorted(offers, key=lambda o: (o.price_quality != "normal", int(o.price_toman or 0), o.offer_id))


class Catalogue:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise FileNotFoundError("Catalogue has not been imported")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path.as_uri() + "?mode=ro&immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        conn.create_function("safe_public_link", 1, lambda value: bool(_safe_link(value)), deterministic=True)
        conn.create_function("compact_model", 1, lambda value: re.sub(r"\W+", "", normalize_text(value)), deterministic=True)
        try:
            yield conn
        finally:
            conn.close()

    def _product(self, row):
        raw = json.loads(row["data"])
        return ProductHit(
            product_id=row["product_id"],
            title=raw.get("persian_title") or None,
            category=raw.get("category_name"),
            brand=raw.get("brand_name"),
            model=raw.get("model"),
            specs=raw.get("specs") or [],
            image_urls=[u for u in raw.get("image_urls") or [] if _safe_link(u)],
            min_recorded_price=str(row["minimum"]) if row["minimum"] is not None else None,
            evidence_ids=[row["product_id"]] + ([row["min_offer_id"]] if row["min_offer_id"] else []),
        )

    def search_products(self, constraints: SearchConstraints, limit=20, *, price_first=False):
        if not 1 <= limit <= 20:
            raise ValueError("Search limit must be1–20")
        normalized_query = normalize_text(constraints.query)
        normalized_query = re.sub(r"(?<!\w)(\d+)\s*(?:gb|گیگابایت|گیگ)(?!\w)", r"\1", normalized_query)
        tokens = re.findall(r"\w+", normalized_query)[:20]
        if not tokens:
            return []
        terms = []
        for token in tokens:
            variants = (
                [token, token + "gb", token + "گیگابایت", token + "گیگ"] if token.isdecimal() else [token]
            )
            if token in ("ram", "رم"):
                variants = ["ram", "رم"]
            terms.append("(" + " OR ".join('"' + v.replace('"', '""') + '"' for v in variants) + ")")
        query = " AND ".join(terms)
        offer_contact = " AND " + _contact_sql("o") if constraints.contactable_only else ""
        sql = f"""SELECT p.*,bm25(product_search) AS rank,
          (SELECT MIN(price) FROM offers o WHERE o.product_id=p.product_id AND price_quality='normal' {offer_contact}) AS minimum,
          (SELECT offer_id FROM offers o WHERE o.product_id=p.product_id AND price_quality='normal' {offer_contact} ORDER BY price,offer_id LIMIT 1) AS min_offer_id
          FROM product_search JOIN products p USING(product_id) WHERE product_search MATCH ?"""
        args = [query]
        if constraints.category:
            sql += " AND p.category=?"
            args.append(constraints.category)
        if constraints.max_price_toman is not None:
            contact_budget = " AND " + _contact_sql("bo") if constraints.contactable_only else ""
            sql += f" AND EXISTS (SELECT 1 FROM offers bo WHERE bo.product_id=p.product_id AND bo.price_quality='normal' AND bo.price<=? {contact_budget})"
            args.append(constraints.max_price_toman)
        if constraints.contactable_only:
            sql += " AND EXISTS (SELECT 1 FROM offers co JOIN shops cs USING(shop_id) WHERE co.product_id=p.product_id AND (safe_public_link(json_extract(cs.data,'$.website_url')) OR safe_public_link(json_extract(cs.data,'$.instagram'))))"
        if price_first:
            sql += " ORDER BY minimum IS NULL,minimum,rank,p.product_id LIMIT 100"
        else:
            sql += " ORDER BY CASE WHEN compact_model(json_extract(p.data, '$.model'))=? THEN 0 ELSE 1 END,rank,p.product_id LIMIT 100"
            args.append(re.sub(r"\W+", "", normalized_query))
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        hits = [self._product(row) for row in rows]
        if constraints.max_price_toman is not None:
            hits = [
                h
                for h in hits
                if h.min_recorded_price is not None
                and int(h.min_recorded_price) <= int(constraints.max_price_toman)
            ]
        normalized = normalize_text(constraints.query)
        if not price_first:
            hits.sort(
                key=lambda h: (re.sub(r"\W+", "", normalize_text(h.model)) != re.sub(r"\W+", "", normalized), normalize_text(h.title) != normalized)
            )
        return hits[:limit]

    def search_locations(self, query, limit=8):
        """Literal address matching over supplied points, not neighborhood geocoding."""
        terms = re.findall(r"\w+", normalize_text(query))[:12]
        if not terms or len("".join(terms)) < 2:
            return []
        matches = []
        with self.connect() as db:
            rows = db.execute("SELECT shop_id,lat,lon,data FROM shops WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY shop_id").fetchall()
        for row in rows:
            raw = json.loads(row["data"])
            address = raw.get("address") or ""
            if address and all(term in normalize_text(address) for term in terms):
                matches.append({"shop_id": row["shop_id"], "label": address, "lat": row["lat"], "lon": row["lon"], "source": "catalogue_shop_coordinate"})
                if len(matches) >= limit:
                    break
        return matches

    def search_diagnostics(self, constraints):
        """Proposed search changes only; never broaden the actual query invisibly."""
        if not constraints.query.strip() or self.search_products(constraints, limit=1):
            return []
        diagnostics = []
        if constraints.category:
            proposed = constraints.model_copy(update={"category": None})
            hits = self.search_products(proposed)
            if hits:
                diagnostics.append({"kind": "category", "constraints": proposed.model_dump(mode="json"), "example_product_id": hits[0].product_id})
        if constraints.max_price_toman is not None:
            proposed = constraints.model_copy(update={"max_price_toman": None})
            hits = self.search_products(proposed, limit=1, price_first=True)
            prices = [int(h.min_recorded_price) for h in hits if h.min_recorded_price is not None]
            if prices:
                minimum = str(min(prices))
                proposed.max_price_toman = minimum
                diagnostics.append({"kind": "budget", "minimum_toman": minimum, "constraints": proposed.model_dump(mode="json")})
        return diagnostics

    def compare_products(self, product_ids, constraints):
        from .types import Mission

        result = []
        for product_id in product_ids:
            product = self.get_product(product_id)
            mission = Mission(id="comparison", session_id="comparison", selected_product_id=product_id, constraints=constraints)
            plan = self.plan_mission(mission)
            reasons = {}
            for option in plan.excluded:
                for reason in option.reason_codes:
                    reasons[reason] = reasons.get(reason, 0) + 1
            result.append({
                "product": product.model_dump(mode="json"),
                "eligible_shops": plan.shortlist_coverage["eligible_shops"],
                "distinct_shops": plan.shortlist_coverage["distinct_shops"],
                "best_offer": plan.primary.offer.model_dump(mode="json") if plan.primary else None,
                "exclusion_reasons": reasons,
            })
        return result

    def get_product(self, product_id):
        with self.connect() as db:
            row = db.execute(
                """SELECT p.*,(SELECT MIN(price) FROM offers o WHERE o.product_id=p.product_id
              AND price_quality='normal') AS minimum,
              (SELECT offer_id FROM offers o WHERE o.product_id=p.product_id AND price_quality='normal' ORDER BY price,offer_id LIMIT 1) AS min_offer_id
              FROM products p WHERE product_id=?""",
                (product_id,),
            ).fetchone()
        if row is None:
            raise KeyError(product_id)
        return self._product(row)

    def find_offers(self, product_id, constraints: SearchConstraints, now=None):
        product = self.get_product(product_id)
        now = constraints.visit_at or now or datetime.now(timezone.utc)
        with self.connect() as db:
            rows = db.execute(
                "SELECT o.*,s.lat,s.lon,s.data AS shop_data FROM offers o JOIN shops s USING(shop_id) WHERE product_id=?",
                (product_id,),
            ).fetchall()
        result = []
        for row in rows:
            raw, shop = json.loads(row["data"]), json.loads(row["shop_data"])
            distance = (
                None
                if row["lat"] is None or row["lon"] is None
                else distance_km(constraints.lat, constraints.lon, row["lat"], row["lon"])
            )
            payment, evidence = payment_state(
                shop.get("payment_options"), constraints.payment_provider, product.category, row["price"]
            )
            links = [
                {"channel": channel, "url": url}
                for channel, field in (("website", "website_url"), ("instagram", "instagram"))
                if (url := _safe_link(shop.get(field)))
            ]
            price = str(row["price"]) if row["price"] is not None else None
            result.append(
                OfferHit(
                    offer_id=row["offer_id"],
                    product_id=product_id,
                    shop_id=row["shop_id"],
                    shop_name=shop.get("name") or "",
                    identity_anonymized=not bool(shop.get("website_url") or shop.get("instagram")),
                    address=shop.get("address") or "",
                    lat=row["lat"],
                    lon=row["lon"],
                    price_toman=price,
                    recorded_price_toman=price,
                    price_quality=row["price_quality"],
                    price_changed_at=raw.get("last_price_changed_at"),
                    straight_line_km=distance,
                    hours_state=hours_state(shop.get("weekly_hours"), now),
                    weekly_hours=shop.get("weekly_hours"),
                    payment_state=payment,
                    payment_evidence=evidence,
                    contact_links=links,
                    seller_title=raw.get("seller_title"),
                    warranty=raw.get("warranty"),
                    evidence_ids=[row["offer_id"], product_id, row["shop_id"]],
                )
            )
        return rank_by_price(result)

    def plan_mission(self, mission, observations=None):
        from .planner import build_plan
        from .followup import apply_observations

        offers = self.find_offers(mission.selected_product_id, mission.constraints)
        category = self.get_product(mission.selected_product_id).category
        return build_plan(mission, apply_observations(mission, offers, observations or [], category))
