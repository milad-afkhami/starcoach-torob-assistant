"""Persistence, cookie ownership and optimistic concurrency must prevent cross-session mutation."""

import pytest
from test_search import catalogue, constraints


def setup(tmp_path):
    from torob.session import Store

    c = catalogue(tmp_path)
    return Store(tmp_path / "state.sqlite", "test-session-secret-at-least-32-chars", c), c


def new_mission(s, owner, mode="assisted", **kw):
    return s.create_mission(owner, "p1", constraints(**kw), mode, now=100)


def test_session_cookie_authentication_expiry_and_restart(tmp_path):
    from torob.session import Store, StoreError

    s, c = setup(tmp_path)
    cookie, owner = s.create_session(100)
    assert s.resolve_session(cookie, 101) == owner
    restarted = Store(tmp_path / "state.sqlite", "test-session-secret-at-least-32-chars", c)
    assert restarted.resolve_session(cookie, 101) == owner
    for value, when in [(None, 101), (cookie + "bad", 101), (cookie, 86501)]:
        with pytest.raises(StoreError) as err:
            s.resolve_session(value, when)
        assert err.value.status == 401


def test_mission_owner_and_revision_guards(tmp_path):
    from torob.session import StoreError

    s, c = setup(tmp_path)
    _, a = s.create_session(100)
    _, b = s.create_session(100)
    m = new_mission(s, a, max_price_toman="250")
    with pytest.raises(StoreError) as err:
        s.get_mission(b, m.id)
    assert err.value.status == 404
    changed = s.patch_mission(a, m.id, 1, {"constraints": {"max_price_toman": "400"}}, 101)
    assert (
        changed.revision == 2 and changed.constraints.radius_km == 1 and changed.selected_product_id == "p1"
    )
    with pytest.raises(StoreError) as err:
        s.patch_mission(a, m.id, 1, {"constraints": {"radius_km": 5}}, 102)
    assert err.value.status == 409
    assert s.get_mission(a, m.id).constraints.radius_km == 1


def test_mission_mode_and_unknown_product_not_mutated(tmp_path):
    from torob.session import StoreError

    s, c = setup(tmp_path)
    _, a = s.create_session(100)
    m = new_mission(s, a)
    for patch in [{"mode": "simulation"}, {"session_id": "foreign"}, {"selected_product_id": "missing"}]:
        with pytest.raises(StoreError):
            s.patch_mission(a, m.id, 1, patch, 101)
    assert s.get_mission(a, m.id).revision == 1


def test_reset_is_simulation_only_and_other_session_untouched(tmp_path):
    from torob.session import StoreError

    s, c = setup(tmp_path)
    _, a = s.create_session(100)
    _, b = s.create_session(100)
    m = new_mission(s, a)
    n = new_mission(s, b, mode="simulation")
    with pytest.raises(StoreError) as err:
        s.reset(a, m.id, 1, 101)
    assert err.value.status == 403
    with pytest.raises(StoreError):
        s.reset(a, n.id, 1, 101)
    assert s.reset(b, n.id, 1, 102).revision == 2
    assert s.get_mission(a, m.id).revision == 1


def test_non_ascii_cookie_is_rejected_not_server_error(tmp_path):
    from torob.session import StoreError

    s, c = setup(tmp_path)
    with pytest.raises(StoreError) as error:
        s.resolve_session("id.امضا", 100)
    assert error.value.status == 401
