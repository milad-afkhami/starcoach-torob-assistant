from datetime import datetime, timezone

from .hours import TEHRAN
from .ingest import SAFE_INTEGER
from .normalize import normalize_text
from .types import PlanDelta

KINDS = {
    "available",
    "unavailable",
    "no_response",
    "price_change",
    "variant_mismatch",
    "payment_conflict",
    "closed",
}


def dimension(observation):
    kind = observation["kind"]
    if kind in ("available", "unavailable", "no_response"):
        return ("availability", observation["product_id"], observation["shop_id"])
    if kind == "price_change":
        return ("price", observation["offer_id"])
    if kind == "variant_mismatch":
        return ("variant", observation["offer_id"])
    if kind == "payment_conflict":
        return (
            "payment",
            observation["product_id"],
            observation["shop_id"],
            observation.get("payment_provider"),
        )
    return ("closed", observation["shop_id"], observation["effective_visit_date"])


def active_observations(observations):
    confirmed = [o for o in observations if o.get("confirmed")]
    superseded = {previous for o in confirmed for previous in o.get("supersedes_ids", [])}
    return [o for o in sorted(confirmed, key=lambda x: x["applied_revision"]) if o["id"] not in superseded]


def apply_observations(mission, offers, observations, category=None):
    active = active_observations(observations)
    quote_ids = {}
    for obs in active:
        if obs["kind"] == "price_change":
            quote_ids.setdefault((obs["product_id"], obs["shop_id"]), set()).add(obs["offer_id"])
    visit = mission.constraints.visit_at or datetime.now(timezone.utc)
    visit_date = visit.astimezone(TEHRAN).date().isoformat()
    result = []
    for original in offers:
        offer = original.model_copy(deep=True)
        offer.recorded_price_quality = original.price_quality
        quotes = quote_ids.get((offer.product_id, offer.shop_id), set())
        if quotes and offer.offer_id not in quotes:
            offer.observation_reasons.append("quote_required")
        for obs in active:
            if obs["shop_id"] != offer.shop_id:
                continue
            if obs["scope"] != "shop_date" and obs["product_id"] != offer.product_id:
                continue
            if obs["scope"] == "offer" and obs["offer_id"] != offer.offer_id:
                continue
            kind = obs["kind"]
            if kind == "closed" and obs["effective_visit_date"] != visit_date:
                continue
            if kind == "payment_conflict" and (
                not mission.constraints.payment_provider
                or normalize_text(mission.constraints.payment_provider)
                != normalize_text(obs.get("payment_provider"))
            ):
                continue
            if kind == "price_change":
                offer.price_toman = obs["price_toman"]
                offer.price_quality = "normal" if 0 < int(obs["price_toman"]) <= SAFE_INTEGER else "flagged"
            elif kind == "unavailable":
                offer.observation_reasons.append("reported_unavailable")
            elif kind == "no_response":
                offer.observation_reasons.append("no_response")
            elif kind == "variant_mismatch":
                offer.observation_reasons.append("variant_mismatch")
            elif kind == "payment_conflict":
                offer.observation_reasons.append("reported_payment_conflict")
            elif kind == "closed":
                offer.observation_reasons.append("reported_closed")
            offer.observation_provenance, offer.observation_id = obs["provenance"], obs["id"]
            offer.observations.append(
                {
                    k: obs.get(k)
                    for k in (
                        "id",
                        "kind",
                        "provenance",
                        "confirmed_at",
                        "applied_revision",
                        "price_toman",
                        "raw_text",
                        "effective_visit_date",
                    )
                }
            )
            offer.evidence_ids.append("observation:" + obs["id"])
        from .catalogue import payment_state

        offer.payment_state, _ = payment_state(
            offer.payment_evidence,
            mission.constraints.payment_provider,
            category,
            int(offer.price_toman) if offer.price_toman is not None else None,
        )
        result.append(offer)
    return result


def compare_plans(before, after, constraints, reason):
    def identity(option):
        return option.offer.offer_id if option else None

    fields = []
    if identity(before.primary) != identity(after.primary):
        fields.append("primary_offer")
    if identity(before.fallback) != identity(after.fallback):
        fields.append("fallback_offer")
    delta = None
    if before.primary and after.primary:
        delta = str(int(after.primary.offer.price_toman) - int(before.primary.offer.price_toman))
        if delta != "0":
            fields.append("price")
    return PlanDelta(
        before_revision=before.revision,
        after_revision=after.revision,
        changed_fields=fields,
        price_delta_toman=delta,
        retained_constraints=list(type(constraints).model_fields),
        reason_codes=[reason],
    )
