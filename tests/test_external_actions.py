from urllib.parse import urlsplit, parse_qs
from test_sessions import setup, new_mission


def test_safe_query_and_transport_destinations_follow_plan(tmp_path):
    from torob.external_actions import build_external_actions

    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner)
    product = c.get_product("p1").model_copy(update={"title": "گوشی & A07 | 128"})
    plan = s.plan(owner, m.id)
    actions = build_external_actions(product, plan.primary, m)
    by = {a["kind"]: a for a in actions}
    assert parse_qs(urlsplit(by["torob_search"]["url"]).query)["query"] == ["گوشی & A07 | 128"]
    assert parse_qs(urlsplit(by["neshan_point"]["url"]).query) == {"lat": ["35.7"], "lng": ["51.4001"]}
    assert by["balad_open"]["url"] == "https://balad.ir/"
    assert by["snapp_open"]["url"] == "https://app.snapp.taxi/"
    assert by["tapsi_open"]["url"] == "https://app.tapsi.cab/"
    assert "torobpay_account" not in by
    assert all(owner not in a["url"] and m.id not in a["url"] for a in actions)
    assert "فروشگاه" not in by["snapp_open"]["destination_text"]
    next_actions = build_external_actions(product, plan.fallback, m.model_copy(update={"revision": 2}))
    assert next(a for a in next_actions if a["kind"] == "neshan_point")["url"] != by["neshan_point"]["url"]
    assert (
        next(a for a in next_actions if a["kind"] == "snapp_open")["destination_text"]
        != by["snapp_open"]["destination_text"]
    )


def test_invalid_coordinates_and_payment_discovery(tmp_path):
    from torob.external_actions import build_external_actions

    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner)
    option = s.plan(owner, m.id).primary.model_copy(deep=True)
    option.offer.lat = None
    m = m.model_copy(update={"constraints": m.constraints.model_copy(update={"payment_provider": "ترب‌پی"})})
    actions = build_external_actions(c.get_product("p1"), option, m)
    assert "neshan_point" not in [a["kind"] for a in actions]
    assert (
        next(a for a in actions if a["kind"] == "torobpay_account")["url"] == "https://torobpay.com/account"
    )
    assert next(a for a in actions if a["kind"] == "balad_open")["destination_text"] == "طبقه اول واحد 1"
