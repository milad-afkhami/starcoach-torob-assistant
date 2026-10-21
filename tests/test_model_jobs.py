"""Queue risks: wrong owner, duplicate claims/results, expiry, public usage amplification."""

import json
import pytest

GOOD = {"action": "HOLD", "evidence_ids": ["e1"]}
SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"enum": ["HOLD"]},
        "evidence_ids": {"type": "array", "items": {"enum": ["e1"]}},
    },
    "required": ["action", "evidence_ids"],
    "additionalProperties": False,
}


def queue(tmp_path):
    from torob.model_jobs import JobQueue

    return JobQueue(tmp_path / "state.sqlite")


def enqueue(q, owner="s1", request="r1", now=100, revision=1, deadline=200):
    return q.enqueue(
        owner=owner,
        request_id=request,
        payload={"e1": "evidence"},
        schema=SCHEMA,
        schema_id="test-v1",
        prompt_version="1",
        deadline=deadline,
        now=now,
        mission_id="m1",
        revision=revision,
    )


def test_worker_unavailable_and_heartbeat_expires(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    with pytest.raises(ModelError, match="unavailable"):
        enqueue(q)
    q.heartbeat("worker", 100)
    enqueue(q)
    with pytest.raises(ModelError, match="unavailable"):
        enqueue(q, owner="s2", now=146)


def test_atomic_claim_only_one_active_and_token_not_persisted_plain(tmp_path):
    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    j = enqueue(q)
    enqueue(q, owner="s2", request="r2")
    claim = q.claim("worker", 101)
    assert claim["id"] == j["id"] and claim["state"] == "leased"
    assert q.claim("other", 101) is None
    assert "completion_token" not in q.get(j["id"], "s1", 101)
    with q.connect() as db:
        row = dict(db.execute("select * from model_jobs where id=?", (j["id"],)).fetchone())
    assert claim["completion_token"] not in json.dumps(row)


def test_result_accept_once_with_matching_owner_revision_and_lease(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    j = enqueue(q)
    c = q.claim("worker", 101)
    result = q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 102)
    assert result["state"] == "completed" and q.get(j["id"], "s1", 103)["result"] == GOOD
    with pytest.raises(ModelError, match="not_found"):
        q.get(j["id"], "s2", 103)
    with pytest.raises(ModelError, match="conflict"):
        q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 103)


@pytest.mark.parametrize("field", ["lease_id", "completion_token"])
def test_wrong_completion_credential_rejected(tmp_path, field):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    enqueue(q)
    c = q.claim("worker", 101)
    c[field] = "wrong"
    with pytest.raises(ModelError, match="conflict"):
        q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 102)


def test_expired_wait_and_expired_lease_never_requeued(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    j = enqueue(q)
    assert q.claim("worker", 116) is None
    assert q.get(j["id"], "s1", 116)["state"] == "expired"
    j = enqueue(q, request="r2", now=120, deadline=160)
    c = q.claim("worker", 121)
    with pytest.raises(ModelError, match="conflict"):
        q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 161)
    assert q.claim("worker", 161) is None and q.get(j["id"], "s1", 161)["state"] == "expired"


def test_cancel_is_owner_only_and_result_after_cancel_rejected(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    j = enqueue(q)
    c = q.claim("worker", 101)
    with pytest.raises(ModelError, match="not_found"):
        q.cancel(j["id"], "s2", 102)
    q.cancel(j["id"], "s1", 102)
    with pytest.raises(ModelError, match="conflict"):
        q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 103)
    assert q.get(j["id"], "s1", 104)["state"] == "canceled"


def test_invalid_result_does_not_complete(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    enqueue(q)
    c = q.claim("worker", 101)
    with pytest.raises(ModelError, match="invalid_output"):
        q.complete(c["id"], c["lease_id"], c["completion_token"], {"action": "BUY"}, 102)
    assert q.get(c["id"], "s1", 103)["state"] == "failed"


def test_global_capacity_and_per_session_outstanding(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    enqueue(q)
    with pytest.raises(ModelError, match="busy"):
        enqueue(q, request="r2")
    enqueue(q, owner="s2", request="r2")
    with pytest.raises(ModelError, match="queue_full"):
        enqueue(q, owner="s3", request="r3")
    q.claim("worker", 101)
    enqueue(q, owner="s3", request="r3", now=101)
    with pytest.raises(ModelError, match="queue_full"):
        enqueue(q, owner="s4", request="r4", now=101)


def test_session_quota_and_restart(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    for n in range(10):
        j = enqueue(q, request=f"r{n}")
        q.cancel(j["id"], "s1", 100)
    with pytest.raises(ModelError, match="rate_limited"):
        enqueue(queue(tmp_path), request="r11")
    q.heartbeat("worker", 3701)
    assert enqueue(q, request="r12", now=3701, deadline=3800)


def test_same_request_correction_does_not_reset_deadline_or_quota(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    for n in range(2):
        enqueue(q, now=100 + n)
        c = q.claim("worker", 100 + n)
        q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 101 + n)
    with pytest.raises(ModelError, match="request_call_limit"):
        enqueue(q, now=103)


def test_stale_revision_is_preserved_not_auto_applied(tmp_path):
    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    enqueue(q, revision=4)
    c = q.claim("worker", 101)
    done = q.complete(c["id"], c["lease_id"], c["completion_token"], GOOD, 102)
    assert done["revision"] == 4 and done["mission_id"] == "m1"
    # Domain consumer must compare this immutable revision against its current mission.


def test_oversized_payload_and_expired_deadline_reject(tmp_path):
    from torob.model_types import ModelError

    q = queue(tmp_path)
    q.heartbeat("worker", 100)
    with pytest.raises(ModelError, match="expired"):
        enqueue(q, deadline=99)
    with pytest.raises(ModelError, match="oversized_input"):
        q.enqueue(
            owner="s1",
            request_id="r1",
            payload={"x": "x" * 50000},
            schema=SCHEMA,
            schema_id="test",
            prompt_version="1",
            deadline=200,
            now=100,
        )
