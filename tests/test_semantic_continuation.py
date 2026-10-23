"""Owned dialogue keeps unresolved intent, source-backed checks and explicit resolution."""

from test_agent import env, finish, intent
from torob.session import StoreError
import pytest


def requirement(quote, kind="location", hard=True, terms=None, numeric=None):
    return {
        "label_fa": quote,
        "source_quote": quote,
        "kind": kind,
        "hard": hard,
        "spec_terms": terms or [],
        "numeric": numeric,
    }


def clarify(a, q, owner, clock):
    first = a.start_turn(owner, "لپ تاپ برای دانشگاه نزدیک انقلاب تا شصت میلیون")
    out = intent("clarify")
    out.update(
        query="لپ تاپ",
        category="لپ تاپ و نوت بوک",
        max_price_toman="60000000",
        clarification_fa="محدوده را انتخاب کن.",
        semantic_requirements=[requirement("نزدیک انقلاب")],
        spec_focus_terms=[],
    )
    finish(q, clock, out)
    return a.get_turn(owner, first["id"])


def test_empty_clarification_is_a_valid_owned_semantic_parent_and_keeps_pending_area(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    first = clarify(a, q, owner, clock)
    follow = a.start_turn(
        owner,
        "بودجه را چهل و پنج میلیون کن و وزن حتما کمتر از 1.5 کیلوگرم باشد",
        semantic_parent_turn_id=first["id"],
    )
    job = q.claim("w", clock[0])
    assert job
    assert job["payload"]["semantic_context"]["pending_clarification_fa"] == "محدوده را انتخاب کن."
    assert job["payload"]["semantic_context"]["requirements"][0]["source_quote"] == "نزدیک انقلاب"
    assert job["payload"]["current_constraints"]["category"] == "لپ تاپ و نوت بوک"
    assert job["payload"]["current_constraints"]["max_price_toman"] == "60000000"
    assert follow["state"] == "running"


@pytest.mark.parametrize("kind", ["foreign", "expired", "future", "failed", "reply"])
def test_invalid_semantic_parent_never_queues_work(tmp_path, kind):
    import json

    a, s, q, owner, clock = env(tmp_path)
    p = clarify(a, q, owner, clock)
    caller = owner
    if kind == "foreign":
        _, caller = s.create_session(clock[0])
    elif kind == "expired":
        clock[0] += 1801
    elif kind == "future":
        clock[0] -= 10
    else:
        with s.connect() as db:
            value = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
            if kind == "failed":
                value["state"] = "failed"
            else:
                value["kind"] = "reply"
            db.execute(
                "UPDATE turns SET state=?,data=? WHERE id=?", (value["state"], json.dumps(value), p["id"])
            )
    with pytest.raises(StoreError):
        a.start_turn(caller, "ادامه بده", semantic_parent_turn_id=p["id"])
    assert q.claim("w", clock[0]) is None


def test_a_fresh_thread_does_not_receive_previous_owners_completed_requests(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    clarify(a, q, owner, clock)
    a.start_turn(owner, "گوشی تازه میخواهم")
    job = q.claim("w", clock[0])
    assert job["payload"]["previous_messages"] == []


def test_no_recommendation_becomes_an_explicit_unresolved_result(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی A07")
    finish(q, clock, intent())
    a.get_turn(owner, t["id"])
    finish(q, clock, {"recommendations": []})
    done = a.get_turn(owner, t["id"])
    assert done["result"]["recommendation_state"] == "unresolved"
    assert done["result"]["clarification_fa"]


def test_later_candidate_with_requested_evidence_reaches_explanation_and_pending_area_survives(tmp_path):
    import json
    from test_agent import recommendation

    a, s, q, owner, clock = env(tmp_path)
    # Add real source rows to the isolated catalogue. The relevant field is beyond
    # the former eight-spec and six-product truncations; no source IDs are invented.
    with a.catalogue.connect() as db:
        original = json.loads(db.execute("SELECT data FROM products WHERE product_id='p1'").fetchone()[0])
    import sqlite3

    with sqlite3.connect(a.catalogue.path) as db:
        for i in range(3, 11):
            row = {
                **original,
                "product_id": f"p{i}",
                "persian_title": f"A07 variant {i}",
                "specs": [{"key": f"generic {n}", "value": "source"} for n in range(12)]
                + ([{"key": "وزن", "value": "1.4 کیلوگرم"}] if i == 10 else []),
            }
            db.execute(
                "INSERT INTO products VALUES(?,?,?,?)",
                (row["product_id"], row["persian_title"], row["category_name"], json.dumps(row)),
            )
            db.execute("INSERT INTO product_search VALUES(?,?)", (row["product_id"], "a07"))
            offer = {
                "offer_id": f"o{i}extra",
                "product_id": row["product_id"],
                "shop_id": "s1",
                "price_toman": "100",
            }
            db.execute(
                "INSERT INTO offers VALUES(?,?,?,?,?,?)",
                (offer["offer_id"], row["product_id"], "s1", 100, "normal", json.dumps(offer)),
            )
    t = a.start_turn(owner, "گوشی A07 با وزن کمتر از 1.5 کیلوگرم نزدیک انقلاب")
    out = intent()
    out.update(
        semantic_requirements=[
            requirement(
                "وزن کمتر از 1.5 کیلوگرم",
                "spec",
                True,
                ["وزن"],
                {"operator": "lt", "value": "1.5", "unit": "kg"},
            ),
            requirement("نزدیک انقلاب"),
        ],
        spec_focus_terms=["وزن"],
    )
    finish(q, clock, out)
    a.get_turn(owner, t["id"])
    job = q.claim("w", clock[0])
    assert job["payload"]["candidates"][0]["product_id"] == "p10"
    assert any(
        f["label"] == "وزن" and f["value"] == "1.4 کیلوگرم" for f in job["payload"]["candidates"][0]["facts"]
    )
    q.complete(job["id"], job["lease_id"], job["completion_token"], recommendation(job), clock[0])
    done = a.get_turn(owner, t["id"])
    assert done["result"]["recommendation_state"] == "unresolved"
    assert done["result"]["recommendations"] == []
    assert done["result"]["location_action"] is True
    assert done["result"]["products"][0]["product_id"] == "p10"
    assert "نزدیک انقلاب" in done["result"]["clarification_fa"]


def test_only_explicit_origin_resolution_clears_pending_location_without_mutating_a_mission(tmp_path):
    from test_search import constraints

    a, s, q, owner, clock = env(tmp_path)
    p = clarify(a, q, owner, clock)
    a.start_turn(
        owner,
        "با مبدأ انتخاب‌شده ادامه بده",
        semantic_parent_turn_id=p["id"],
        origin_confirmed=True,
        constraints=constraints().model_copy(
            update={"lat": 35.8, "lon": 51.5, "origin_label": "نقطه انتخابی"}
        ),
    )
    job = q.claim("w", clock[0])
    assert job["payload"]["semantic_context"]["requirements"][0]["origin_resolved"] is True
    assert job["payload"]["current_constraints"]["lat"] == 35.8
    assert job["payload"]["current_constraints"]["max_price_toman"] == "60000000"


def test_invented_semantic_quote_cannot_become_a_user_constraint(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی A07")
    out = intent()
    out["semantic_requirements"] = [requirement("کاربر هرگز این را نگفت")]
    finish(q, clock, out)
    assert a.get_turn(owner, t["id"])["state"] == "failed"


@pytest.mark.parametrize("downgrade", [False, True])
def test_omitted_or_downgraded_explicit_hard_condition_never_becomes_verified(tmp_path, downgrade):
    from test_agent import recommendation

    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی A07 میخواهم و وزن حتما کمتر از 1.5 کیلوگرم باشد")
    out = intent()
    if downgrade:
        out["semantic_requirements"] = [
            requirement(
                "وزن حتما کمتر از 1.5 کیلوگرم باشد",
                "spec",
                False,
                ["وزن"],
                {"operator": "lt", "value": "1.5", "unit": "kg"},
            )
        ]
    finish(q, clock, out)
    a.get_turn(owner, t["id"])
    job = q.claim("w", clock[0])
    assert job
    q.complete(job["id"], job["lease_id"], job["completion_token"], recommendation(job), clock[0])
    result = a.get_turn(owner, t["id"])["result"]
    assert result["recommendation_state"] == "unresolved" and result["recommendations"] == []
    assert any(r["hard"] for r in result["semantic_context"]["requirements"])


def test_semantic_parent_is_bound_to_its_owned_mission_scope(tmp_path):
    from test_sessions import new_mission

    a, s, q, owner, clock = env(tmp_path)
    mission = new_mission(s, owner)
    t = a.start_turn(owner, "بودجه را بررسی کن", mission_id=mission.id, base_revision=1)
    finish(q, clock, intent())
    assert a.get_turn(owner, t["id"])["state"] == "completed"
    other = new_mission(s, owner)
    with pytest.raises(StoreError):
        a.start_turn(
            owner, "ادامه بده", mission_id=other.id, base_revision=1, semantic_parent_turn_id=t["id"]
        )
    assert q.claim("w", clock[0]) is None
    valid = a.start_turn(
        owner, "ادامه بده", mission_id=mission.id, base_revision=1, semantic_parent_turn_id=t["id"]
    )
    assert valid["state"] == "running"


def test_discovery_and_semantic_parents_cannot_describe_different_responses(tmp_path):
    from test_discovery_context import parent

    a, s, q, owner, clock = env(tmp_path)
    semantic = clarify(a, q, owner, clock)
    cards = parent(a, q, owner, clock)
    with pytest.raises(StoreError):
        a.start_turn(
            owner,
            "دومی را مقایسه کن",
            semantic_parent_turn_id=semantic["id"],
            discovery_parent_turn_id=cards["id"],
        )
    assert q.claim("w", clock[0]) is None


def test_origin_confirmation_cannot_bypass_an_owned_missions_explicit_condition_update(tmp_path):
    from test_sessions import new_mission
    from test_search import constraints

    a, s, q, owner, clock = env(tmp_path)
    mission = new_mission(s, owner)
    t = a.start_turn(owner, "بودجه را بررسی کن", mission_id=mission.id, base_revision=1)
    finish(q, clock, intent())
    a.get_turn(owner, t["id"])
    with pytest.raises(StoreError):
        a.start_turn(
            owner,
            "ادامه با مبدأ انتخابی",
            mission_id=mission.id,
            base_revision=1,
            semantic_parent_turn_id=t["id"],
            origin_confirmed=True,
            constraints=constraints().model_copy(update={"lat": 35.8}),
        )
    assert s.get_mission(owner, mission.id).revision == 1
    assert q.claim("w", clock[0]) is None
