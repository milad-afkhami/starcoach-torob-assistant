"""Confirmed session observations repair a mission without corrupting source or weakening constraints."""

import pytest
from catalogue_fixtures import records
from test_search import catalogue
from test_sessions import setup, new_mission


def preview(s, owner, m, offer="o1", kind="unavailable", **kw):
    f = s.create_followup(owner, m.id, offer, now=101)
    return s.preview_observation(
        owner, m.id, f["id"], m.revision, kind, raw_text="پاسخ فروشنده", now=102, **kw
    )


def confirmed(s, owner, m, **kw):
    o = preview(s, owner, m, **kw)
    return s.confirm_observation(owner, m.id, o["id"], m.revision, now=103)


def test_unavailability_repairs_without_changing_constraints_or_catalogue(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, max_price_toman="300")
    before = c.path.read_bytes()
    plan, delta = confirmed(s, owner, m)
    assert plan.primary.offer.offer_id == "o2" and plan.fallback.offer.offer_id == "o3"
    assert delta.price_delta_toman == "100"
    assert s.get_mission(owner, m.id).constraints == m.constraints
    assert s.get_mission(owner, m.id).selected_product_id == "p1"
    assert c.path.read_bytes() == before
    assert s.observations(owner, m.id)[0]["provenance"] == "user_reported"


def test_preview_does_not_apply_until_confirmed(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner)
    preview(s, owner, m)
    assert s.plan(owner, m.id).primary.offer.offer_id == "o1"
    assert s.get_mission(owner, m.id).revision == 1


def test_stale_preview_and_foreign_confirmation_fail(tmp_path):
    from torob.session import StoreError

    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    _, other = s.create_session(100)
    m = new_mission(s, owner)
    obs = preview(s, owner, m)
    with pytest.raises(StoreError) as err:
        s.confirm_observation(other, m.id, obs["id"], 1, now=103)
    assert err.value.status == 404
    s.patch_mission(owner, m.id, 1, {"constraints": {"max_price_toman": "400"}}, 103)
    with pytest.raises(StoreError) as err:
        s.confirm_observation(owner, m.id, obs["id"], 1, now=104)
    assert err.value.status == 409 and s.observations(owner, m.id) == []


def test_price_change_preserves_old_price_and_exact_delta(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, max_price_toman="300")
    plan, delta = confirmed(s, owner, m, kind="price_change", price_toman="350")
    assert plan.primary.offer.offer_id == "o2"
    excluded = next(o for o in plan.excluded if o.offer.offer_id == "o1")
    assert excluded.offer.price_toman == "350" and excluded.offer.recorded_price_toman == "100"
    assert excluded.offer.observation_provenance == "user_reported"
    assert delta.price_delta_toman == "100"


def test_no_response_is_unknown_and_not_promoted_when_exhausted(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, max_price_toman="100")
    plan, _ = confirmed(s, owner, m, kind="no_response")
    assert plan.primary is None and plan.fallback is None
    item = next(o for o in plan.excluded if o.offer.offer_id == "o1")
    assert item.eligibility == "needs_verification" and "no_response" in item.reason_codes
    assert item.offer.stock_state == "unknown"


def test_available_reply_explicitly_supersedes_unavailability(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner)
    confirmed(s, owner, m)
    m = s.get_mission(owner, m.id)
    old = s.observations(owner, m.id)[0]
    obs = preview(s, owner, m, kind="available")
    assert obs["supersedes_ids"] == [old["id"]]
    plan, _ = s.confirm_observation(owner, m.id, obs["id"], m.revision, now=105)
    assert plan.primary.offer.offer_id == "o1"
    assert plan.primary.offer.stock_state == "unknown"
    assert len(s.observations(owner, m.id)) == 2


def test_closed_today_not_applied_to_tomorrow(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner)
    plan, _ = confirmed(s, owner, m, kind="closed", effective_visit_date="2026-10-21")
    assert plan.primary.offer.offer_id == "o1"
    m = s.get_mission(owner, m.id)
    plan, _ = confirmed(s, owner, m, kind="closed", effective_visit_date="2026-10-22")
    assert plan.primary.offer.offer_id == "o2"


def test_wrong_variant_and_payment_conflict_do_not_change_product(tmp_path):
    from torob.session import Store

    rows = records()
    for shop in rows["shops.csv"]:
        shop["payment_options"] = [
            {
                "provider_name": "ترب‌پی",
                "channel": "in_person",
                "category_names": ["گوشی موبایل"],
                "min_price_toman": None,
                "max_price_toman": None,
            }
        ]
    c = catalogue(tmp_path, rows)
    s = Store(tmp_path / "state.sqlite", "test-session-secret-at-least-32-chars", c)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, payment_provider="ترب‌پی")
    plan, _ = confirmed(s, owner, m, kind="variant_mismatch")
    assert plan.primary.offer.offer_id == "o2"
    assert s.get_mission(owner, m.id).selected_product_id == "p1"
    m = s.get_mission(owner, m.id)
    plan, _ = confirmed(s, owner, m, offer="o2", kind="payment_conflict")
    assert plan.primary.offer.offer_id == "o3"
    m = s.get_mission(owner, m.id)
    s.patch_mission(owner, m.id, m.revision, {"constraints": {"payment_provider": None}}, 104)
    assert s.plan(owner, m.id).primary.offer.offer_id == "o2"


def test_simulation_provenance_and_reset(tmp_path):
    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, mode="simulation")
    confirmed(s, owner, m)
    assert s.observations(owner, m.id)[0]["provenance"] == "simulation"
    s.reset(owner, m.id, 2, 105)
    assert s.plan(owner, m.id).primary.offer.offer_id == "o1"
    assert s.observations(owner, m.id) == []


def test_duplicate_shop_cannot_bypass_reported_price_or_no_response(tmp_path):
    from torob.session import Store

    rows = records()
    rows["offers.csv"].append({**rows["offers.csv"][0], "offer_id": "o4", "price_toman": 101})
    c = catalogue(tmp_path, rows)
    s = Store(tmp_path / "state.sqlite", "test-session-secret-at-least-32-chars", c)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, max_price_toman="150")
    plan, _ = confirmed(s, owner, m, kind="price_change", price_toman="160")
    assert plan.primary is None
    duplicate = next(o for o in plan.excluded if o.offer.offer_id == "o4")
    assert duplicate.eligibility == "needs_verification" and "quote_required" in duplicate.reason_codes
    m = s.get_mission(owner, m.id)
    plan, _ = confirmed(s, owner, m, offer="o4", kind="price_change", price_toman="120")
    assert plan.primary.offer.offer_id == "o4"
    m = s.get_mission(owner, m.id)
    plan, _ = confirmed(s, owner, m, offer="o4", kind="no_response")
    assert plan.primary is None


def test_invalid_observation_never_changes_state(tmp_path):
    from torob.session import StoreError

    s, c = setup(tmp_path)
    _, owner = s.create_session(100)
    m = new_mission(s, owner)
    for kind, args in [
        ("price_change", {}),
        ("closed", {}),
        ("invented", {}),
        ("price_change", {"price_toman": "-1"}),
    ]:
        with pytest.raises(StoreError):
            preview(s, owner, m, kind=kind, **args)
    assert s.get_mission(owner, m.id).revision == 1


def test_new_quote_rechecks_recorded_payment_amount_limits(tmp_path):
    from torob.session import Store

    rows = records()
    for shop in rows["shops.csv"]:
        shop["payment_options"] = [
            {
                "provider_name": "ترب‌پی",
                "channel": "in_person",
                "category_names": ["گوشی موبایل"],
                "min_price_toman": None,
                "max_price_toman": 150,
            }
        ]
    c = catalogue(tmp_path, rows)
    s = Store(tmp_path / "state.sqlite", "test-session-secret-at-least-32-chars", c)
    _, owner = s.create_session(100)
    m = new_mission(s, owner, payment_provider="ترب‌پی", max_price_toman="500")
    plan, _ = confirmed(s, owner, m, kind="price_change", price_toman="160")
    assert plan.primary is None
    assert next(o for o in plan.excluded if o.offer.offer_id == "o1").offer.payment_state == "unsupported"
