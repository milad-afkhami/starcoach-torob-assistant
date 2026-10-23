"""Discovery pronouns refer only to exact owned, completed, displayed source cards."""

import json
import pytest
from test_agent import env, finish, intent
from test_sessions import new_mission
from torob.session import StoreError


def parent(a, q, owner, clock):
    t = a.start_turn(owner, "A07 و قاب آن را نشان بده")
    out = intent("compare")
    out.update(query="", category=None, max_price_toman=None, comparison_queries=["A07", "قاب A07"])
    finish(q, clock, out)
    a.get_turn(owner, t["id"])
    job = q.claim("w", clock[0])
    choices = [
        {
            "product_id": p["product_id"],
            "reason_fa": "از داده ثبت شده است.",
            "fact_ids": [p["facts"][0]["id"]],
        }
        for p in reversed(job["payload"]["candidates"][:2])
    ]
    q.complete(job["id"], job["lease_id"], job["completion_token"], {"recommendations": choices}, clock[0])
    return a.get_turn(owner, t["id"])


def test_reference_order_is_display_order_not_recommendation_order(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    assert [x["product_id"] for x in p["result"]["products"]] == ["p1", "p2"]
    assert [x["product_id"] for x in p["result"]["recommendations"]] == ["p2", "p1"]
    t = a.start_turn(owner, "دومی را با اولی مقایسه کن", discovery_parent_turn_id=p["id"])
    job = q.claim("w", clock[0])
    assert job["prompt_version"] == "torob-semantic-v2"
    refs = job["payload"]["discovery_context"]["products"]
    assert [(r["display_position"], r["product_id"]) for r in refs] == [(1, "p1"), (2, "p2")]
    assert job["schema"]["properties"]["reference_product_ids"]["items"]["enum"] == ["p1", "p2"]
    out = intent("compare")
    out.update(comparison_queries=[], reference_product_ids=["p2", "p1"], max_price_toman="999")
    q.complete(job["id"], job["lease_id"], job["completion_token"], out, clock[0])
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed"
    assert [x["product_id"] for x in done["result"]["products"]] == ["p2", "p1"]
    assert done["result"]["comparison_product_ids"] == ["p2", "p1"]
    assert done["result"]["proposed_constraints"]["max_price_toman"] is None
    assert not any(x["tool"] == "search_products" for x in done["trace"])


@pytest.mark.parametrize(
    "invalid",
    ["foreign", "expired", "failed", "canceled", "reply", "parent_mission", "child_mission", "empty"],
)
def test_parent_rejection_matrix_never_queues_a_model_job(tmp_path, invalid):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    caller = owner
    kw = {}
    if invalid == "foreign":
        _, caller = s.create_session(clock[0])
    elif invalid == "expired":
        clock[0] += 1801
    elif invalid == "child_mission":
        m = new_mission(s, owner)
        kw = {"mission_id": m.id, "base_revision": m.revision}
    else:
        with s.connect() as db:
            value = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
            if invalid in ("failed", "canceled"):
                value["state"] = invalid
            elif invalid == "reply":
                value["kind"] = "reply"
            elif invalid == "parent_mission":
                value["mission_id"] = "owned-mission"
            elif invalid == "empty":
                value["result"]["products"] = []
            db.execute(
                "UPDATE turns SET state=?,data=? WHERE id=?", (value["state"], json.dumps(value), p["id"])
            )
    with s.connect() as db:
        before = db.execute("SELECT COUNT(*) FROM model_jobs").fetchone()[0]
    with pytest.raises(StoreError):
        a.start_turn(caller, "دومی را مقایسه کن", discovery_parent_turn_id=p["id"], **kw)
    with s.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM model_jobs").fetchone()[0] == before


def test_unknown_reference_cannot_escape_dynamic_source_allowlist(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    t = a.start_turn(owner, "دومی را مقایسه کن", discovery_parent_turn_id=p["id"])
    out = intent("compare")
    out.update(comparison_queries=[], reference_product_ids=["p1", "foreign"])
    from torob.model_types import ModelError

    with pytest.raises(ModelError):
        finish(q, clock, out)
    assert a.get_turn(owner, t["id"])["state"] == "failed"


def test_ambiguous_memory_clarifies_without_model_or_mutating_mission(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    m = new_mission(s, owner, max_price_toman="250")
    with s.connect() as db:
        before = db.execute("SELECT COUNT(*) FROM model_jobs").fetchone()[0]
    done = a.start_turn(owner, "همان مدل با حافظه بیشتر", discovery_parent_turn_id=p["id"])
    assert (
        done["state"] == "completed"
        and "رم" in done["result"]["clarification_fa"]
        and "داخلی" in done["result"]["clarification_fa"]
    )
    assert [x["product_id"] for x in done["result"]["products"]] == ["p1", "p2"]
    assert s.get_mission(owner, m.id).constraints.max_price_toman == "250"
    with s.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM model_jobs").fetchone()[0] == before


def test_ordinal_without_valid_parent_asks_instead_of_guessing(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    done = a.start_turn(owner, "دومی را با اولی مقایسه کن")
    assert done["state"] == "completed" and done["result"]["products"] == []
    assert done["result"]["clarification_fa"]
    assert q.claim("w", clock[0]) is None


def test_related_search_cannot_escape_referenced_model_family(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    t = a.start_turn(owner, "گزینه اول را در همین خانواده بررسی کن", discovery_parent_turn_id=p["id"])
    out = intent()
    out.update(query="A07", category=None, max_price_toman=None, reference_product_ids=["p1"])
    finish(q, clock, out)
    assert a.get_turn(owner, t["id"])["stage"] == "explain"
    job = q.claim("w", clock[0])
    assert [p["product_id"] for p in job["payload"]["candidates"]] == ["p1"]


def test_duplicate_reference_ids_are_not_a_two_product_comparison(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    t = a.start_turn(owner, "دومی را مقایسه کن", discovery_parent_turn_id=p["id"])
    out = intent("compare")
    out.update(comparison_queries=[], reference_product_ids=["p1", "p1"])
    finish(q, clock, out)
    assert a.get_turn(owner, t["id"])["state"] == "failed"


def test_missing_references_cannot_guess_ordinal_via_new_text_search(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    t = a.start_turn(owner, "دومی را با اولی مقایسه کن", discovery_parent_turn_id=p["id"])
    out = intent("compare")
    out.update(comparison_queries=["A07", "قاب A07"], reference_product_ids=[])
    finish(q, clock, out)
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed" and done["result"]["clarification_fa"]
    assert [x["product_id"] for x in done["result"]["products"]] == ["p1", "p2"]
    assert not any(x["tool"] == "search_products" for x in done["trace"])


def test_unavailable_ordinal_is_not_guessed_or_queued(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    with s.connect() as db:
        before = db.execute("SELECT COUNT(*) FROM model_jobs").fetchone()[0]
    done = a.start_turn(owner, "هفتمی را با اولی مقایسه کن", discovery_parent_turn_id=p["id"])
    assert done["state"] == "completed" and done["result"]["clarification_fa"]
    with s.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM model_jobs").fetchone()[0] == before


def expanded_parent(a, s, q, owner, clock):
    from copy import deepcopy
    from catalogue_fixtures import records
    from test_search import catalogue

    rows = records()
    for i in range(3, 9):
        product = deepcopy(rows["products.csv"][0])
        product["product_id"] = f"p{i}"
        rows["products.csv"].append(product)
    a.catalogue = catalogue(s.path.parent if hasattr(s, "path") else q.path.parent, rows)
    p = parent(a, q, owner, clock)
    with s.connect() as db:
        v = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
        v["result"]["products"] = [
            a.catalogue.get_product(f"p{i}").model_dump(mode="json") for i in range(1, 9)
        ]
        v["result"]["products"][0]["min_recorded_price"] = "200"
        v["result"]["products"][0]["evidence_ids"] = ["p1", "o2"]
        db.execute("UPDATE turns SET data=? WHERE id=?", (json.dumps(v), p["id"]))
    return p


@pytest.mark.parametrize(
    "branch",
    [
        "ambiguous_memory",
        "model_clarify",
        "invalid_resolution",
        "one_reference_compare",
        "missing_family",
        "no_hits",
    ],
)
def test_every_contextual_clarification_preserves_full_eight_displayed_cards(tmp_path, branch):
    a, s, q, owner, clock = env(tmp_path)
    p = expanded_parent(a, s, q, owner, clock)
    message = "همان مدل با حافظه بیشتر" if branch == "ambiguous_memory" else "نیاز به راهنمایی دارم"
    t = a.start_turn(owner, message, discovery_parent_turn_id=p["id"])
    if t["state"] != "completed":
        out = intent("clarify" if branch == "model_clarify" else "search")
        out.update(reference_product_ids=[], max_price_toman=None)
        if branch == "invalid_resolution":
            out.update(action="search", reference_product_ids=["p1", "p2"])
        elif branch == "one_reference_compare":
            out.update(action="compare", reference_product_ids=["p1"])
        elif branch == "missing_family":
            out.update(reference_product_ids=["p2"])
        elif branch == "no_hits":
            out.update(query="unmatched-model-xyz")
        finish(q, clock, out)
        t = a.get_turn(owner, t["id"])
    assert t["state"] == "completed" and t["result"]["clarification_fa"]
    assert [p["product_id"] for p in t["result"]["products"]] == [f"p{i}" for i in range(1, 9)]
    assert t["result"]["products"][0]["min_recorded_price"] == "200"
    assert t["result"]["products"][0]["evidence_ids"] == ["p1", "o2"]


@pytest.mark.parametrize(
    "message",
    [
        "گزینه ۷ را با گزینه ۱ مقایسه کن",
        "گزینه 7 را با گزینه 1 مقایسه کن",
        "کارت ٧ را با کارت ١ مقایسه کن",
        "گزینه شماره ۷ را با گزینه شماره ۱ مقایسه کن",
        "۷ام را با ۱ام مقایسه کن",
        "گزینه ۰ را مقایسه کن",
    ],
)
def test_numeric_reference_forms_fail_closed_before_model_for_unavailable_position(tmp_path, message):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    t = a.start_turn(owner, message, discovery_parent_turn_id=p["id"])
    assert t["state"] == "completed" and t["result"]["clarification_fa"]
    assert [x["product_id"] for x in t["result"]["products"]] == ["p1", "p2"]
    assert q.claim("w", clock[0]) is None


@pytest.mark.parametrize(
    "message", ["همان مدل با رم بیشتر", "همین مدل با فضای ذخیره بیشتر", "همون مدل با رم بیشتر"]
)
def test_same_model_reference_cannot_omit_binding_and_return_accessory(tmp_path, message):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    with s.connect() as db:
        v = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
        v["result"]["products"] = v["result"]["products"][:1]
        db.execute("UPDATE turns SET data=? WHERE id=?", (json.dumps(v), p["id"]))
    t = a.start_turn(owner, message, discovery_parent_turn_id=p["id"])
    out = intent()
    out.update(query="قاب A07", category=None, max_price_toman=None, reference_product_ids=[])
    finish(q, clock, out)
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed" and done["result"]["clarification_fa"]
    assert [x["product_id"] for x in done["result"]["products"]] == ["p1"]
    assert not any(x["tool"] == "search_products" for x in done["trace"])


@pytest.mark.parametrize(
    "message",
    [
        "گزینه ۲ را با گزینه ۱ مقایسه کن",
        "کارت ٢ را با کارت ١ مقایسه کن",
        "گزینه 2 را با گزینه 1 مقایسه کن",
        "۲ام را با ۱ام مقایسه کن",
    ],
)
def test_numeric_reference_order_binds_exact_display_positions(tmp_path, message):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    t = a.start_turn(owner, message, discovery_parent_turn_id=p["id"])
    out = intent("compare")
    out.update(reference_product_ids=["p1", "p2"], comparison_queries=[])
    finish(q, clock, out)
    done = a.get_turn(owner, t["id"])
    assert done["result"]["comparison_product_ids"] == ["p2", "p1"]


def test_single_same_model_reference_with_exact_binding_filters_accessories(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    with s.connect() as db:
        v = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
        v["result"]["products"] = v["result"]["products"][:1]
        db.execute("UPDATE turns SET data=? WHERE id=?", (json.dumps(v), p["id"]))
    t = a.start_turn(owner, "همان مدل با رم بیشتر", discovery_parent_turn_id=p["id"])
    out = intent()
    out.update(query="A07", category=None, max_price_toman=None, reference_product_ids=["p1"])
    finish(q, clock, out)
    assert a.get_turn(owner, t["id"])["stage"] == "explain"
    job = q.claim("w", clock[0])
    assert [x["product_id"] for x in job["payload"]["candidates"]] == ["p1"]


def test_clarification_preserves_displayed_price_scope_and_offer_evidence(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    with s.connect() as db:
        v = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
        # A source search may have a narrower contact filter than get_product's global price.
        v["result"]["products"][0]["min_recorded_price"] = "200"
        v["result"]["products"][0]["evidence_ids"] = ["p1", "o2"]
        db.execute("UPDATE turns SET data=? WHERE id=?", (json.dumps(v), p["id"]))
    done = a.start_turn(owner, "همان مدل با حافظه بیشتر", discovery_parent_turn_id=p["id"])
    assert done["result"]["products"][0]["min_recorded_price"] == "200"
    assert done["result"]["products"][0]["evidence_ids"] == ["p1", "o2"]


@pytest.mark.parametrize(
    "message,expected",
    [("اولی را با دومی مقایسه کن", ["p1", "p2"]), ("دومی را با اولی مقایسه کن", ["p2", "p1"])],
)
def test_reference_comparison_preserves_full_snapshot_price_scope_and_requested_order(
    tmp_path, message, expected
):
    from test_search import constraints

    a, s, q, owner, clock = env(tmp_path)
    p = parent(a, q, owner, clock)
    with s.connect() as db:
        v = json.loads(db.execute("SELECT data FROM turns WHERE id=?", (p["id"],)).fetchone()[0])
        v["result"]["products"][0]["min_recorded_price"] = "200"
        v["result"]["products"][0]["evidence_ids"] = ["p1", "o2"]
        snapshots = {x["product_id"]: x for x in v["result"]["products"]}
        db.execute("UPDATE turns SET data=? WHERE id=?", (json.dumps(v), p["id"]))
    c = constraints(contactable_only=True)
    t = a.start_turn(owner, message, constraints=c, discovery_parent_turn_id=p["id"])
    out = intent("compare")
    out.update(reference_product_ids=["p1", "p2"], comparison_queries=[])
    finish(q, clock, out)
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed"
    assert done["result"]["comparison_product_ids"] == expected
    assert done["result"]["products"] == [snapshots[x] for x in expected]
    assert done["result"]["proposed_constraints"] == c.model_dump(mode="json")
    assert (
        a.catalogue.get_product("p1").min_recorded_price == "100"
    )  # Global source is intentionally different.
