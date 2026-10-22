from .catalogue import distance_km
from .types import PlanOption, PurchasePlan


def classify_offer(offer, constraints):
    conflict, missing = [], []
    for reason in offer.observation_reasons:
        (missing if reason in ("no_response", "quote_required") else conflict).append(reason)
    if offer.price_quality != "normal":
        missing.append("price_" + offer.price_quality)
    elif constraints.max_price_toman is not None and int(offer.price_toman) > int(
        constraints.max_price_toman
    ):
        conflict.append("over_budget")
    if offer.straight_line_km is None:
        missing.append("location_unknown")
    elif offer.straight_line_km > constraints.radius_km:
        conflict.append("outside_radius")
    if constraints.require_declared_open:
        if offer.hours_state == "closed":
            conflict.append("closed_at_visit")
        elif offer.hours_state == "unknown":
            missing.append("hours_unknown")
    if constraints.payment_provider:
        if offer.payment_state == "unknown":
            missing.append("payment_unknown")
        elif offer.payment_state == "unsupported":
            conflict.append("payment_conflict")
    return PlanOption(
        offer=offer,
        eligibility="ineligible" if conflict else "needs_verification" if missing else "candidate",
        reason_codes=conflict + missing,
        unresolved_checks=["current_price", "current_stock"]
        + (["buyer_credit_and_payment_terms"] if constraints.payment_provider else []),
    )


def build_plan(mission, offers):
    options = [classify_offer(o, mission.constraints) for o in offers]
    eligible = [o for o in options if o.eligibility == "candidate"]
    by_shop = {}
    for option in sorted(eligible, key=lambda o: (int(o.offer.price_toman), o.offer.offer_id)):
        by_shop.setdefault(option.offer.shop_id, option)
    distinct = list(by_shop.values())
    cheapest = sorted(
        distinct, key=lambda o: (int(o.offer.price_toman), o.offer.straight_line_km, o.offer.shop_id)
    )
    nearest = sorted(
        distinct, key=lambda o: (o.offer.straight_line_km, int(o.offer.price_toman), o.offer.shop_id)
    )
    shortlist = {o.offer.shop_id: o for o in cheapest[:30] + nearest[:30]}
    excluded = [o for o in options if o.eligibility != "candidate"]
    # Preserve the newest reported/recheckable seller before bounding the response.
    # Price order alone can hide it behind dozens of cheaper ineligible offers.
    excluded.sort(
        key=lambda option: max(
            (obs.get("applied_revision") or 0 for obs in option.offer.observations), default=0
        ),
        reverse=True,
    )
    coverage = {
        "distinct_shops": len({o.shop_id for o in offers}),
        "eligible_shops": len(distinct),
        "shortlisted_shops": len(shortlist),
        "excluded_offers": len(excluded),
    }
    if not shortlist:
        return PurchasePlan(
            revision=mission.revision,
            primary=None,
            fallback=None,
            choices=[],
            excluded=excluded[:60],
            shortlist_coverage=coverage,
        )

    def separation(a, b):
        return distance_km(a.offer.lat, a.offer.lon, b.offer.lat, b.offer.lon)

    def backups(option):
        return [
            other
            for other in shortlist.values()
            if other.offer.shop_id != option.offer.shop_id and separation(option, other) <= 0.5
        ]

    primary = shortlist.get(mission.selected_primary_shop_id) or cheapest[0]
    fallback = min(
        backups(primary),
        key=lambda o: (int(o.offer.price_toman), o.offer.straight_line_km, o.offer.shop_id),
        default=None,
    )
    resilient = min(
        shortlist.values(),
        key=lambda o: (-len(backups(o)), int(o.offer.price_toman), o.offer.straight_line_km, o.offer.shop_id),
    )
    choices = {}
    for label, option in (
        ("cheapest", cheapest[0]),
        ("closest", nearest[0]),
        ("nearby_alternatives", resilient),
    ):
        current = choices.setdefault(option.offer.shop_id, option.model_copy(deep=True))
        current.tradeoffs.append(label)
    return PurchasePlan(
        revision=mission.revision,
        primary=primary,
        fallback=fallback,
        choices=list(choices.values()),
        excluded=excluded[:60],
        shortlist_coverage=coverage,
    )
