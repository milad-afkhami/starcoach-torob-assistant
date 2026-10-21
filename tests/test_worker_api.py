"""Worker boundary: auth, validation, correct lifecycle, no cookie privilege escalation."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from test_model_jobs import enqueue, queue, GOOD


def setup(tmp_path):
    from torob.worker_api import worker_router

    q = queue(tmp_path)
    app = FastAPI()
    clock = [100.0]
    app.include_router(worker_router(q, "test-secret-32-chars-or-more-12345", lambda: clock[0]))
    return TestClient(app), q, clock


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Cookie": "session=owner"}])
def test_worker_auth_is_separate_from_user_session(tmp_path, headers):
    c, q, clock = setup(tmp_path)
    assert (
        c.post("/internal/model-worker/heartbeat", json={"worker_id": "w"}, headers=headers).status_code
        == 401
    )
    assert not q.available(100)


def auth():
    return {"Authorization": "Bearer test-secret-32-chars-or-more-12345"}


def test_worker_complete_lifecycle_and_no_secret_return(tmp_path):
    c, q, clock = setup(tmp_path)
    assert (
        c.post("/internal/model-worker/heartbeat", json={"worker_id": "w"}, headers=auth()).status_code == 200
    )
    j = enqueue(q)
    response = c.post("/internal/model-worker/claim", json={"worker_id": "w"}, headers=auth())
    assert response.status_code == 200
    claim = response.json()["job"]
    assert claim["id"] == j["id"]
    body = {"lease_id": claim["lease_id"], "completion_token": claim["completion_token"], "result": GOOD}
    response = c.post(f"/internal/model-worker/jobs/{j['id']}/complete", json=body, headers=auth())
    assert response.status_code == 200 and response.json()["state"] == "completed"
    assert "token_hash" not in response.text and "completion_token" not in response.text
    assert (
        c.post(f"/internal/model-worker/jobs/{j['id']}/complete", json=body, headers=auth()).status_code
        == 409
    )


def test_invalid_worker_and_large_request_reject(tmp_path):
    c, q, clock = setup(tmp_path)
    assert (
        c.post("/internal/model-worker/heartbeat", json={"worker_id": ""}, headers=auth()).status_code == 422
    )
    assert (
        c.post(
            "/internal/model-worker/heartbeat", json={"worker_id": "w", "extra": 1}, headers=auth()
        ).status_code
        == 422
    )
    assert c.post("/internal/model-worker/heartbeat", content="x" * 70000, headers=auth()).status_code == 413


def test_worker_status_other_worker_denied_and_fail(tmp_path):
    c, q, clock = setup(tmp_path)
    q.heartbeat("w", 100)
    j = enqueue(q)
    claim = q.claim("w", 101)
    path = f"/internal/model-worker/jobs/{j['id']}"
    assert c.get(path + "?worker_id=other", headers=auth()).status_code == 404
    assert c.get(path + "?worker_id=w", headers=auth()).json()["state"] == "leased"
    body = {
        "lease_id": claim["lease_id"],
        "completion_token": claim["completion_token"],
        "error_code": "budget_exhausted",
    }
    assert c.post(path + "/fail", json=body, headers=auth()).status_code == 200
    assert q.get(j["id"], "s1", 101)["error_code"] == "budget_exhausted"


def test_worker_provenance_is_typed_and_stored(tmp_path):
    c, q, clock = setup(tmp_path)
    q.heartbeat("w", 100)
    j = enqueue(q)
    claim = q.claim("w", 101)
    provenance = {
        "provider": "codex_cli",
        "model": "gpt-6.1-sol",
        "cli_version": "0.163.0",
        "elapsed_ms": 9000,
    }
    body = {
        "lease_id": claim["lease_id"],
        "completion_token": claim["completion_token"],
        "result": GOOD,
        "provenance": provenance,
    }
    response = c.post(f"/internal/model-worker/jobs/{j['id']}/complete", json=body, headers=auth())
    assert response.status_code == 200
    assert q.get(j["id"], "s1", 101)["provenance"] == provenance
