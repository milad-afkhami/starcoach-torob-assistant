"""Grounding, conversation stages, cancellation and stale-result rejection."""

import pytest
from test_sessions import setup, new_mission


def env(tmp_path):
    from torob.agent import AgentService
    from torob.model_jobs import JobQueue

    store, c = setup(tmp_path)
    _, owner = store.create_session(100)
    queue = JobQueue(tmp_path / "state.sqlite")
    queue.heartbeat("w", 100)
    clock = [100.0]
    return AgentService(store, queue, c, lambda: clock[0]), store, queue, owner, clock


def finish(queue, clock, value):
    claim = queue.claim("w", clock[0])
    assert claim
    clock[0] += 1
    queue.complete(
        claim["id"],
        claim["lease_id"],
        claim["completion_token"],
        value,
        clock[0],
        {"provider": "codex_cli", "model": "test", "cli_version": "test", "elapsed_ms": 1},
    )
    return claim


def intent(action="search"):
    return {
        "action": action,
        "comparison_queries": [],
        "query": "A07",
        "category": "گوشی موبایل",
        "max_price_toman": "300",
        "clarification_fa": "بودجه شما چقدر است؟" if action == "clarify" else None,
        "condition_changes": None,
    }


def recommendation(job):
    product = job["payload"]["candidates"][0]
    return {
        "recommendations": [
            {
                "product_id": product["product_id"],
                "reason_fa": "این گزینه با مشخصات ثبت‌شده قابل بررسی است.",
                "fact_ids": [product["facts"][0]["id"]],
            }
        ]
    }


def test_needs_search_explain_and_grounded_ids(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی A07 تا سیصد تومان")
    finish(q, clock, intent())
    stage = a.get_turn(owner, t["id"])
    assert stage["state"] == "running" and stage["stage"] == "explain"
    claim = q.claim("w", clock[0])
    result = recommendation(claim)
    clock[0] += 1
    q.complete(claim["id"], claim["lease_id"], claim["completion_token"], result, clock[0])
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed" and done["result"]["products"][0]["product_id"] == "p1"
    assert done["result"]["recommendations"][0]["product_id"] == "p1"
    assert done["result"]["proposed_constraints"]["max_price_toman"] == "300"
    assert len(done["trace"]) <= 6
    assert a.get_turn(owner, t["id"]) == done
    assert q.claim("w", clock[0]) is None


def test_clarification_is_real_result_without_fake_products(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی خوب میخوام")
    finish(q, clock, intent("clarify"))
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed" and done["result"]["clarification_fa"] == "بودجه شما چقدر است؟"
    assert done["result"]["products"] == [] and q.claim("w", clock[0]) is None


def test_provider_outage_returns_explicit_degraded_state(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    clock[0] = 146
    t = a.start_turn(owner, "گوشی")
    assert t["state"] == "failed" and t["error_code"] == "unavailable"
    assert t["result"]["degraded"] is True


def test_foreign_owner_and_cancellation(tmp_path):
    from torob.session import StoreError

    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی")
    with pytest.raises(StoreError) as err:
        a.get_turn("foreign", t["id"])
    assert err.value.status == 404
    a.cancel_turn(owner, t["id"])
    assert a.get_turn(owner, t["id"])["state"] == "canceled"
    assert q.claim("w", clock[0]) is None


def test_existing_mission_is_not_changed_by_model_suggestion(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    m = new_mission(s, owner, max_price_toman="100")
    t = a.start_turn(owner, "بودجه را بیشتر کنیم", mission_id=m.id, base_revision=1)
    finish(q, clock, intent())
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed"
    assert q.claim("w", clock[0]) is None
    assert s.get_mission(owner, m.id).constraints.max_price_toman == "100"
    assert s.get_mission(owner, m.id).revision == 1


def test_stale_model_response_rejected(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    m = new_mission(s, owner)
    t = a.start_turn(owner, "گوشی", mission_id=m.id, base_revision=1)
    s.patch_mission(owner, m.id, 1, {"constraints": {"radius_km": 2}}, 101)
    finish(q, clock, intent())
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "failed" and done["error_code"] == "stale_revision"
    assert q.claim("w", clock[0]) is None


def test_reply_creates_preview_only_and_keeps_raw_text(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    m = new_mission(s, owner)
    f = s.create_followup(owner, m.id, "o1", 100)
    t = a.start_turn(owner, "موجود نیست", kind="reply", mission_id=m.id, base_revision=1, followup_id=f["id"])
    finish(
        q,
        clock,
        {
            "kind": "unavailable",
            "price_toman": None,
            "effective_visit_date": None,
            "reason_fa": "فروشنده نبود موجودی را گزارش کرده است.",
        },
    )
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed" and done["result"]["observation"]["raw_text"] == "موجود نیست"
    assert s.plan(owner, m.id).primary.offer.offer_id == "o1"
    obs = done["result"]["observation"]
    s.confirm_observation(owner, m.id, obs["id"], 1, 102)
    assert s.plan(owner, m.id).primary.offer.offer_id == "o2"


def test_unclear_reply_never_makes_availability_claim(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    m = new_mission(s, owner)
    f = s.create_followup(owner, m.id, "o1", 100)
    t = a.start_turn(owner, "سلام", kind="reply", mission_id=m.id, base_revision=1, followup_id=f["id"])
    finish(
        q,
        clock,
        {
            "kind": "unclear",
            "price_toman": None,
            "effective_visit_date": None,
            "reason_fa": "پاسخ برای تشخیص کافی نیست.",
        },
    )
    done = a.get_turn(owner, t["id"])
    assert done["result"]["observation"] is None
    assert s.observations(owner, m.id) == []


def test_unrelated_fact_or_model_numeric_claim_rejected(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "گوشی")
    finish(q, clock, intent())
    a.get_turn(owner, t["id"])
    claim = q.claim("w", clock[0])
    clock[0] += 1
    value = recommendation(claim)
    value["recommendations"][0]["reason_fa"] = "باتری آن 999 ساعت دوام دارد"
    q.complete(claim["id"], claim["lease_id"], claim["completion_token"], value, clock[0])
    done = a.get_turn(owner, t["id"])
    assert (
        done["state"] == "failed" and done["result"]["recommendations"] == [] and done["result"]["products"]
    )


def test_one_active_turn_per_owner_and_invalid_reply_input(tmp_path):
    from torob.session import StoreError

    a, s, q, owner, clock = env(tmp_path)
    a.start_turn(owner, "گوشی")
    with pytest.raises(StoreError) as err:
        a.start_turn(owner, "باز هم گوشی")
    assert err.value.status == 409
    with pytest.raises(StoreError):
        a.start_turn(owner, "متن", kind="reply")


def test_comparison_uses_two_searches_not_an_impossible_and_query(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    t = a.start_turn(owner, "A07 را با قاب A07 مقایسه کن")
    value = intent()
    value.update(
        action="compare", query="", comparison_queries=["A07", "قاب A07"], category=None, max_price_toman=None
    )
    finish(q, clock, value)
    stage = a.get_turn(owner, t["id"])
    assert stage["stage"] == "explain"
    claim = q.claim("w", clock[0])
    assert {"p1", "p2"} <= {p["product_id"] for p in claim["payload"]["candidates"]}


def test_clarification_keeps_extracted_proposal_and_selected_product_context(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    m = new_mission(s, owner, max_price_toman="400")
    t = a.start_turn(owner, "بودجه را کمتر کن", mission_id=m.id, base_revision=1)
    claim = q.claim("w", clock[0])
    assert claim["payload"]["selected_product"]["product_id"] == "p1"
    assert claim["payload"]["selected_product"]["title"] == "گوشي سامسونگ A07 ۱۲۸"
    value = intent("clarify")
    value["max_price_toman"] = "390"
    value["clarification_fa"] = "بودجه را کم کردم؛ کدام مدل؟"
    clock[0] += 1
    q.complete(claim["id"], claim["lease_id"], claim["completion_token"], value, clock[0])
    done = a.get_turn(owner, t["id"])
    assert done["result"]["proposed_constraints"]["max_price_toman"] == "390"
    assert s.get_mission(owner, m.id).constraints.max_price_toman == "400"
    assert done["result"]["clarification_fa"] != value["clarification_fa"]


def test_owned_budget_proposal_uses_locked_product_id_not_reidentification(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    m = new_mission(s, owner, max_price_toman="400")
    t = a.start_turn(owner, "بودجه را تغییر بده", mission_id=m.id, base_revision=1)
    value = intent()
    value.update(query="unfindable RAM wording", max_price_toman="410")
    finish(q, clock, value)
    done = a.get_turn(owner, t["id"])
    assert done["state"] == "completed"
    assert [p["product_id"] for p in done["result"]["products"]] == ["p1"]
    assert q.claim("w", clock[0]) is None
    assert s.get_mission(owner, m.id).constraints.max_price_toman == "400"


def test_retention_clears_turn_copies_but_preserves_recent_turn_and_domain_history(tmp_path):
    a, s, q, owner, clock = env(tmp_path)
    old = a.start_turn(owner, "PRIVATE_MODEL_REQUEST_TO_PURGE")
    finish(q, clock, intent("clarify"))
    a.get_turn(owner, old["id"])
    m = new_mission(s, owner, mode="simulation")
    f = s.create_followup(owner, m.id, "o1", clock[0])
    o = s.preview_observation(
        owner, m.id, f["id"], 1, "unavailable", raw_text="DOMAIN_REPORT_TO_KEEP", now=clock[0]
    )
    s.confirm_observation(owner, m.id, o["id"], 1, clock[0])
    clock[0] = 86501
    q.expire(clock[0])
    with s.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM turns WHERE id=?", (old["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT payload FROM model_jobs").fetchone()[0] == "{}"
    assert s.observations(owner, m.id)[0]["raw_text"] == "DOMAIN_REPORT_TO_KEEP"
    _, fresh_owner = s.create_session(clock[0])
    q.heartbeat("w", clock[0])
    recent = a.start_turn(fresh_owner, "RECENT_REQUEST_TO_KEEP")
    q.expire(clock[0] + 1)
    assert a.get_turn(fresh_owner, recent["id"])["state"] == "running"


@pytest.mark.parametrize("trigger", ["startup", "heartbeat", "capability"])
def test_retention_runs_without_a_new_shopping_turn(tmp_path, trigger):
    from torob.agent import AgentService

    a, s, q, owner, clock = env(tmp_path)
    old = a.start_turn(owner, "OLD_PRIVATE_MESSAGE")
    clock[0] = 86501
    if trigger == "startup":
        AgentService(s, q, a.catalogue, lambda: clock[0])
    elif trigger == "heartbeat":
        q.heartbeat("w", clock[0])
    else:
        q.available(clock[0])
    with s.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM turns WHERE id=?", (old["id"],)).fetchone()[0] == 0


def test_requested_radius_visit_and_payment_are_previewed_without_mutating_mission(tmp_path):
    a, store, queue, owner, clock = env(tmp_path)
    mission = new_mission(store, owner)
    before = store.get_mission(owner, mission.id).constraints.model_dump(mode='json')
    turn = a.start_turn(owner, 'شعاع پنج کیلومتر فردا ساعت یازده با ترب پی', mission_id=mission.id, base_revision=mission.revision)
    value = intent('clarify')
    value['condition_changes'] = {'radius_km': 5, 'visit_at': '2026-10-23T11:00:00+03:30', 'payment_provider': 'ترب‌پی', 'require_declared_open': True}
    finish(queue, clock, value)
    done = a.get_turn(owner, turn['id'])
    assert done['state'] == 'completed'
    assert done['result']['proposed_constraints']['radius_km'] == 5
    assert done['result']['proposed_constraints']['visit_at'] == '2026-10-23T11:00:00+03:30'
    assert done['result']['proposed_constraints']['payment_provider'] == 'ترب‌پی'
    assert store.get_mission(owner, mission.id).constraints.model_dump(mode='json') == before


def test_invalid_requested_visit_without_timezone_fails_closed(tmp_path):
    a, store, queue, owner, clock = env(tmp_path)
    turn = a.start_turn(owner, 'فردا ساعت یازده')
    value = intent('clarify')
    value['condition_changes'] = {'radius_km': None, 'visit_at': '2026-10-23T11:00:00', 'payment_provider': None, 'require_declared_open': None}
    finish(queue, clock, value)
    assert a.get_turn(owner, turn['id'])['state'] == 'failed'


def test_no_product_under_budget_explains_the_price_blocker_without_raising_budget(tmp_path):
    a, store, queue, owner, clock = env(tmp_path)
    turn = a.start_turn(owner, 'A07 تا پنجاه تومان')
    value = intent()
    value['max_price_toman'] = '50'
    finish(queue, clock, value)
    done = a.get_turn(owner, turn['id'])
    assert done['state'] == 'completed'
    assert done['result']['products'] == []
    assert 'بودجه' in done['result']['clarification_fa']
    assert '100' in done['result']['clarification_fa']
    assert done['result']['proposed_constraints']['max_price_toman'] == '50'


def test_existing_product_condition_update_finishes_after_interpretation_without_recommending_it_again(tmp_path):
    a, store, queue, owner, clock = env(tmp_path)
    mission = new_mission(store, owner, max_price_toman='400')
    turn = a.start_turn(owner, 'بودجه را به چهارصد و ده تغییر بده', mission_id=mission.id, base_revision=1)
    value = intent()
    value['max_price_toman'] = '410'
    finish(queue, clock, value)
    done = a.get_turn(owner, turn['id'])
    assert done['state'] == 'completed'
    assert done['result']['products'][0]['product_id'] == 'p1'
    assert done['result']['recommendations'] == []
    assert 'فروشگاه' in done['result']['clarification_fa']
    assert 'موجودی' in done['result']['clarification_fa']
    assert queue.claim('w', clock[0]) is None
    assert store.get_mission(owner, mission.id).constraints.max_price_toman == '400'


def test_recommendation_facts_prioritize_decision_specs_but_keep_original_source_indexes():
    from torob.agent import source_facts
    specs = [{'key':f'detail-{i}','value':str(i)} for i in range(15)] + [
        {'key':'ظرفیت باتری','value':'۵۰۰۰ میلی‌آمپر ساعت'},
        {'key':'حافظه داخلی','value':'۱۲۸ گیگابایت'},
        {'key':'حافظه رم','value':'۴ گیگابایت'},
        {'key':'رزولوشن دوربین اصلی','value':'۵۰ مگاپیکسل'},
    ]
    facts=source_facts({'product_id':'p','title':'گوشی','specs':specs,'evidence_ids':['p']})
    assert {'p:spec:15','p:spec:16','p:spec:17','p:spec:18'} <= {f['id'] for f in facts}
    assert next(f for f in facts if f['id']=='p:spec:16')['value'] == '۱۲۸ گیگابایت'
    assert all(f['evidence_ids']==['p'] for f in facts)
