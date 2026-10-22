import math
from urllib.parse import urlencode


def build_external_actions(product, option, mission):
    actions = []

    def add(kind, label, url, *, destination=None, prefill="none"):
        actions.append(
            {
                "kind": kind,
                "label": label,
                "url": url,
                "destination_text": destination,
                "prefill": prefill,
                "offer_id": option.offer.offer_id if option else None,
                "mission_revision": mission.revision,
            }
        )

    query = product.title or product.model
    if query:
        add(
            "torob_search",
            "بررسی همین کالا در ترب",
            "https://torob.com/search/?" + urlencode({"query": query}),
        )
    if mission.constraints.payment_provider:
        add("torobpay_account", "بررسی حساب ترب‌پی", "https://torobpay.com/account")
    if option:
        offer = option.offer
        valid = (
            offer.lat is not None
            and offer.lon is not None
            and math.isfinite(offer.lat)
            and math.isfinite(offer.lon)
            and -90 <= offer.lat <= 90
            and -180 <= offer.lon <= 180
        )
        destination = offer.address
        if valid:
            destination += f"\n{offer.lat}, {offer.lon}"
            add(
                "neshan_point",
                "نشان",
                "https://nshn.ir/?" + urlencode({"lat": offer.lat, "lng": offer.lon}),
                destination=destination,
                prefill="destination",
            )
        for kind, label, url in (
            ("balad_open", "بلد", "https://balad.ir/"),
            ("snapp_open", "اسنپ", "https://app.snapp.taxi/"),
            ("tapsi_open", "تپسی", "https://app.tapsi.cab/"),
        ):
            add(kind, label, url, destination=destination)
    return actions
