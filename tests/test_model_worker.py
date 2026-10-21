"""Worker risks: sending bearer elsewhere, orphan inference on cancel, losing lease identity."""

import json
import time
import pytest
import httpx
from test_codex_cli import GOOD, SCHEMA, fake, client


def job():
    return {
        "id": "j1",
        "request_id": "r1",
        "state": "leased",
        "lease_id": "lease",
        "completion_token": "nonce",
        "payload": {"question": "سلام"},
        "schema": SCHEMA,
        "schema_id": "probe",
        "prompt_version": "1",
        "expires": time.time() + 60,
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://user:pass@example.com",
        "https://example.com/?token=x",
        "http://127.0.0.1",
    ],
)
def test_worker_rejects_unapproved_origin(tmp_path, url):
    from torob.model_worker import PullWorker

    with pytest.raises(ValueError):
        PullWorker(url, "x" * 32, client(tmp_path, fake()))


def test_worker_roundtrip_and_opaque_lease(tmp_path):
    from torob.model_worker import PullWorker

    requests = []

    def handler(req):
        requests.append(req)
        assert req.headers["authorization"] == "Bearer " + "x" * 32
        if req.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={"available": True})
        if req.url.path.endswith("/claim"):
            return httpx.Response(200, json={"job": job()})
        if req.url.path.endswith("/complete"):
            body = json.loads(req.content)
            assert (
                body["result"] == GOOD and body["completion_token"] == "nonce" and body["lease_id"] == "lease"
            )
            assert body["provenance"]["provider"] == "codex_cli"
            return httpx.Response(200, json={"state": "completed"})
        raise AssertionError(req.url)

    w = PullWorker(
        "https://model.example", "x" * 32, client(tmp_path, fake()), transport=httpx.MockTransport(handler)
    )
    assert w.once() == "completed"
    assert len(requests) == 3


def test_worker_cancels_model_when_host_cancels(tmp_path):
    from torob.model_worker import PullWorker
    from torob.model_types import ModelError

    canceled = []

    def slow(spec, cancel):
        assert cancel.wait(3)
        canceled.append(True)
        raise ModelError("canceled")

    def handler(req):
        if req.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={})
        if req.url.path.endswith("/claim"):
            return httpx.Response(200, json={"job": job()})
        if req.method == "GET":
            return httpx.Response(200, json={"state": "canceled"})
        if req.url.path.endswith("/fail"):
            return httpx.Response(409, json={"detail": "conflict"})
        raise AssertionError(req.url)

    w = PullWorker(
        "https://model.example",
        "x" * 32,
        client(tmp_path, slow),
        transport=httpx.MockTransport(handler),
        poll_seconds=0.05,
    )
    assert w.once() == "canceled" and canceled == [True]


def test_idle_worker_does_not_spend_budget(tmp_path):
    from torob.model_worker import PullWorker

    def handler(req):
        return httpx.Response(200, json={"job": None})

    c = client(tmp_path, fake())
    assert (
        PullWorker("https://model.example", "x" * 32, c, transport=httpx.MockTransport(handler)).once()
        == "idle"
    )
    assert not (tmp_path / "gate" / "starts.json").exists()


def test_redirect_never_forwards_secret(tmp_path):
    from torob.model_worker import PullWorker

    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(302, headers={"location": "https://other.invalid"})

    w = PullWorker(
        "https://model.example", "x" * 32, client(tmp_path, fake()), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(httpx.HTTPStatusError):
        w.once()
    assert len(seen) == 1


def test_lost_lease_result_is_discarded_not_reported_completed(tmp_path):
    from torob.model_worker import PullWorker

    def handler(req):
        if req.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={})
        if req.url.path.endswith("/claim"):
            return httpx.Response(200, json={"job": job()})
        return httpx.Response(409, json={"detail": "conflict"})

    w = PullWorker(
        "https://model.example", "x" * 32, client(tmp_path, fake()), transport=httpx.MockTransport(handler)
    )
    assert w.once() == "discarded"


def test_owner_stop_cancels_running_model(tmp_path):
    import threading
    from torob.model_worker import PullWorker
    from torob.model_types import ModelError

    stop = threading.Event()

    def slow(spec, cancel):
        stop.set()
        assert cancel.wait(1)
        raise ModelError("canceled")

    def handler(req):
        if req.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={})
        if req.url.path.endswith("/claim"):
            return httpx.Response(200, json={"job": job()})
        if req.method == "GET":
            return httpx.Response(200, json={"state": "leased"})
        return httpx.Response(200, json={"state": "failed"})

    w = PullWorker(
        "https://model.example",
        "x" * 32,
        client(tmp_path, slow),
        transport=httpx.MockTransport(handler),
        poll_seconds=0.05,
    )
    assert w.once(stop) == "canceled"


def test_idle_heartbeats_are_bounded_to_fifteen_seconds(tmp_path):
    from torob.model_worker import PullWorker

    clock = [0.0]
    heartbeats = []

    def handler(req):
        if req.url.path.endswith("/heartbeat"):
            heartbeats.append(clock[0])
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"job": None})

    w = PullWorker(
        "https://model.example",
        "x" * 32,
        client(tmp_path, fake()),
        transport=httpx.MockTransport(handler),
        clock=lambda: clock[0],
    )
    w.once()
    clock[0] = 1
    w.once()
    clock[0] = 14.9
    w.once()
    clock[0] = 15
    w.once()
    assert heartbeats == [0.0, 15]
