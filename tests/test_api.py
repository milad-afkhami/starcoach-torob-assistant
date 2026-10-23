"""Public/read versus owner/write boundary, exact responses and real persistence."""

from fastapi.testclient import TestClient
from catalogue_fixtures import archive
from torob.ingest import ingest_archive

SECRET = "test-session-secret-at-least-32-chars"
TOKEN = "test-worker-secret-at-least-32-chars"
ORIGIN = "http://testserver"


def application(tmp_path, missing=False):
    from torob.api import create_app

    path = tmp_path / "catalogue.sqlite"
    if not missing:
        ingest_archive(archive(tmp_path), path, expected_hashes={})
    return create_app(
        catalogue_path=path,
        state_db_path=tmp_path / "state.sqlite",
        session_secret=SECRET,
        worker_token=TOKEN,
        public_origin=ORIGIN,
        clock=lambda: 100.0,
    )


def login(app):
    c = TestClient(app)
    c.headers["origin"] = ORIGIN
    response = c.post("/api/sessions")
    assert response.status_code == 200
    return c


def create(c, mode="simulation"):
    response = c.post(
        "/api/missions",
        json={
            "product_id": "p1",
            "mode": mode,
            "constraints": {
                "lat": 35.7,
                "lon": 51.4,
                "max_price_toman": "300",
                "visit_at": "2026-10-22T20:15:00+03:30",
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["mission"]


def test_health_readiness_and_public_catalogue(tmp_path):
    c = TestClient(application(tmp_path))
    assert c.get("/healthz").json() == {"status": "ok"}
    assert c.get("/readyz").status_code == 200
    r = c.post("/api/search", json={"query": "A07", "category": "گوشی موبایل"})
    assert r.status_code == 200 and r.json()["products"][0]["product_id"] == "p1"
    assert c.get("/api/products/p1").status_code == 200
    assert c.get("/api/products/absent").status_code == 404


def test_missing_catalogue_is_not_ready(tmp_path):
    c = TestClient(application(tmp_path, missing=True))
    assert c.get("/healthz").status_code == 200 and c.get("/readyz").status_code == 503
    assert c.post("/api/search", json={"query": "A07"}).status_code == 503


def test_mutations_need_session_and_same_origin(tmp_path):
    c = TestClient(application(tmp_path))
    c.headers["origin"] = ORIGIN
    assert c.post("/api/missions", json={"product_id": "p1", "constraints": {}}).status_code == 401
    c.headers["origin"] = "https://other.invalid"
    assert c.post("/api/sessions").status_code == 403
    c.headers.pop("origin")
    assert c.post("/api/sessions").status_code == 403


def test_cookie_and_cross_session_mission_isolation(tmp_path):
    app = application(tmp_path)
    a = login(app)
    b = login(app)
    m = create(a)
    assert "HttpOnly" in a.post("/api/sessions").headers.get("set-cookie", "") or a.cookies.get(
        "torob_session"
    )
    assert a.get(f"/api/missions/{m['id']}").status_code == 200
    assert b.get(f"/api/missions/{m['id']}").status_code == 404
    assert (
        b.patch(
            f"/api/missions/{m['id']}",
            json={"expected_revision": 1, "constraints": {"max_price_toman": "999"}},
        ).status_code
        == 404
    )
    assert "session_id" not in a.get(f"/api/missions/{m['id']}").json()["mission"]


def test_preview_confirm_recovery_and_stale_revision(tmp_path):
    app = application(tmp_path)
    c = login(app)
    m = create(c)
    mid = m["id"]
    f = c.post(f"/api/missions/{mid}/followups", json={"offer_id": "o1"}).json()
    obs = c.post(
        f"/api/missions/{mid}/observations/preview",
        json={
            "followup_id": f["id"],
            "expected_revision": 1,
            "kind": "unavailable",
            "raw_text": "موجود نیست",
        },
    ).json()
    assert c.get(f"/api/missions/{mid}/plan").json()["primary"]["offer"]["offer_id"] == "o1"
    r = c.post(f"/api/missions/{mid}/observations/{obs['id']}/confirm", json={"expected_revision": 1})
    assert r.status_code == 200 and r.json()["plan"]["primary"]["offer"]["offer_id"] == "o2"
    assert r.json()["delta"]["price_delta_toman"] == "100"
    assert r.json()["plan"]["primary"]["offer"]["stock_state"] == "unknown"
    assert (
        c.post(
            f"/api/missions/{mid}/observations/{obs['id']}/confirm", json={"expected_revision": 1}
        ).status_code
        == 409
    )
    assert c.get(f"/api/missions/{mid}/history").json()["events"][0]["reason_codes"] == ["unavailable"]


def test_invalid_input_and_no_phone_actions(tmp_path):
    c = login(application(tmp_path))
    m = create(c)
    assert c.post("/api/search", json={"query": "A07", "max_price_toman": 100}).status_code == 422
    assert c.post("/api/search", content="x" * 70000).status_code == 413
    assert (
        c.patch(f"/api/missions/{m['id']}", json={"expected_revision": 1, "mode": "assisted"}).status_code
        == 422
    )
    assert "02100000000" not in c.get(f"/api/missions/{m['id']}/plan").text
    assert c.post(f"/api/missions/{m['id']}/followups", json={"offer_id": "foreign"}).status_code == 404


def test_restart_retains_cookie_mission_and_simulation_reset(tmp_path):
    app = application(tmp_path)
    c = login(app)
    m = create(c)
    from torob.api import create_app

    restarted = create_app(
        catalogue_path=tmp_path / "catalogue.sqlite",
        state_db_path=tmp_path / "state.sqlite",
        session_secret=SECRET,
        worker_token=TOKEN,
        public_origin=ORIGIN,
        clock=lambda: 100.0,
    )
    d = TestClient(restarted)
    d.cookies.update(c.cookies)
    d.headers["origin"] = ORIGIN
    assert d.get(f"/api/missions/{m['id']}").status_code == 200
    assert d.post(f"/api/missions/{m['id']}/reset", json={"expected_revision": 1}).status_code == 200
    assert d.get(f"/api/missions/{m['id']}").json()["mission"]["revision"] == 2


def test_session_creation_rate_limit(tmp_path):
    c = TestClient(application(tmp_path))
    c.headers["origin"] = ORIGIN
    for _ in range(10):
        c.cookies.clear()
        assert c.post("/api/sessions").status_code == 200
    c.cookies.clear()
    assert c.post("/api/sessions").status_code == 429


def test_turn_start_poll_cancel_and_foreign_owner(tmp_path):
    app = application(tmp_path)
    a = login(app)
    b = login(app)
    app.state.jobs.heartbeat("w", 100)
    response = a.post("/api/turns", json={"message": "گوشی A07"})
    assert response.status_code == 202
    turn = response.json()
    assert turn["state"] == "running"
    assert b.get(f"/api/turns/{turn['id']}").status_code == 404
    assert a.get(f"/api/turns/{turn['id']}").json()["state"] == "running"
    assert a.post(f"/api/turns/{turn['id']}/cancel").json()["state"] == "canceled"
    assert app.state.jobs.claim("w", 100) is None


def test_public_offers_query_validation(tmp_path):
    c = TestClient(application(tmp_path))
    response = c.get(
        "/api/products/p1/offers", params={"lat": 35.7, "lon": 51.4, "visit_at": "2026-10-22T20:15:00+03:30"}
    )
    assert response.status_code == 200 and len(response.json()["offers"]) == 3
    assert c.get("/api/products/p1/offers", params={"lat": 100}).status_code == 422


def test_frontend_assets_do_not_expose_catalogue(tmp_path):
    from torob.api import create_app

    dist = tmp_path / "ui"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Plan B</title>")
    application(tmp_path)
    app = create_app(
        catalogue_path=tmp_path / "catalogue.sqlite",
        state_db_path=tmp_path / "state.sqlite",
        session_secret=SECRET,
        worker_token=TOKEN,
        public_origin=ORIGIN,
        frontend_dist=dist,
    )
    c = TestClient(app)
    assert c.get("/").status_code == 200 and "Plan B" in c.get("/").text
    assert c.get("/data/catalogue.sqlite").status_code == 404
    assert c.get("/readyz").status_code == 200


def test_session_reuse_does_not_consume_creation_quota(tmp_path):
    app = application(tmp_path)
    c = login(app)
    cookie = c.cookies.get('torob_session')
    for _ in range(12):
        assert c.post('/api/sessions').status_code == 200
        assert c.cookies.get('torob_session') == cookie


def test_purchase_discovery_endpoints_and_revision_checked_acceptance(tmp_path):
    c = login(application(tmp_path))
    assert c.get('/api/locations?q=%25').status_code == 200
    assert c.get('/api/locations?q=' + 'a'*101).status_code == 422
    response = c.post('/api/search', json={'query':'A07','max_price_toman':'99'})
    assert response.json()['products'] == []
    assert response.json()['diagnostics'][0]['minimum_toman'] == '100'
    r = c.post('/api/products/compare', json={'product_ids':['p1','p2'],'constraints':{'lat':35.7,'lon':51.4,'require_declared_open':False}})
    assert r.status_code == 200 and r.json()['products'][0]['eligible_shops'] == 3
    assert c.post('/api/products/compare', json={'product_ids':['p1','absent'],'constraints':{}}).status_code == 404
    assert c.post('/api/products/compare', json={'product_ids':['p1']*3,'constraints':{}}).status_code == 422
    m = create(c)
    mid = m['id']
    no_match = c.patch(f'/api/missions/{mid}', json={'expected_revision':1,'constraints':{'max_price_toman':'99'}}).json()
    proposal = no_match['plan']['relaxations'][0]
    assert c.get(f'/api/missions/{mid}').json()['mission']['constraints']['max_price_toman'] == '99'
    accepted = c.patch(f'/api/missions/{mid}', json={'expected_revision':proposal['base_revision'],'constraints':proposal['constraints']})
    assert accepted.status_code == 200 and accepted.json()['plan']['primary']['offer']['price_toman'] == '100'
    assert c.patch(f'/api/missions/{mid}', json={'expected_revision':proposal['base_revision'],'constraints':proposal['constraints']}).status_code == 409


def test_origin_label_is_additive_preserved_and_bounded(tmp_path):
    c=login(application(tmp_path))
    m=create(c)
    mid=m['id']
    response=c.patch(f'/api/missions/{mid}',json={'expected_revision':1,'constraints':{'origin_label':'نقطه ثبت‌شده تجریش','require_declared_open':False}})
    assert response.status_code==200
    response=c.patch(f'/api/missions/{mid}',json={'expected_revision':2,'constraints':{'max_price_toman':'200'}})
    assert response.json()['mission']['constraints']['origin_label']=='نقطه ثبت‌شده تجریش'
    assert response.json()['mission']['constraints']['require_declared_open'] is False
    assert c.patch(f'/api/missions/{mid}',json={'expected_revision':3,'constraints':{'origin_label':'a'*301}}).status_code==422
