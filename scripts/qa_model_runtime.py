"""Real HTTP + isolated Codex QA. Run with PYTHONPATH=backend and CODEX_* paths.

No credential value or completion nonce is written. Three CLI starts maximum.
Temporary DB/server are owned by this process; unrelated containers are never removed.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone

from fastapi import FastAPI
import httpx
import uvicorn

from torob.codex_cli import CodexCliClient
from torob.model_jobs import JobQueue
from torob.model_types import ModelError
from torob.model_worker import PullWorker
from torob.worker_api import worker_router

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["HOLD"]},
        "evidence_ids": {"type": "array", "items": {"enum": ["fixture-1"]}},
        "reason_fa": {"type": "string"},
    },
    "required": ["action", "evidence_ids", "reason_fa"],
    "additionalProperties": False,
}
GOOD = {"action": "HOLD", "evidence_ids": ["fixture-1"], "reason_fa": "اطلاعات کافی نیست."}
PREFIX = "/internal/model-worker"
LABEL = "starcoach.model=torob"


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=15, check=True)
    return result.stdout


def containers():
    return set(docker("ps", "-aq", "--filter", f"label={LABEL}").split())


def expect_error(fn, code):
    try:
        fn()
    except ModelError as exc:
        assert exc.code == code, (exc.code, code)
        return exc.code
    raise AssertionError(f"Expected {code}")


def run(args):
    token = secrets.token_urlsafe(48)
    evidence = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "rows": {},
        "http": [],
        "runtime": "real Uvicorn TCP / production JobQueue, worker_router, PullWorker, CodexCliClient",
        "fixture": "Synthetic Persian HOLD; no private shopping evidence",
        "model_starts": 0,
    }
    claims = {}
    baseline = containers()
    observed = set()
    stop = threading.Event()
    server = None
    server_thread = None
    workers = []
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def save():
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")

    def check(row, fn):
        began = time.monotonic()
        try:
            details = fn()
            evidence["rows"][str(row)] = {
                "status": "pass",
                "elapsed_seconds": round(time.monotonic() - began, 3),
                "details": details,
            }
            print(f"row {row}: PASS", flush=True)
        except Exception as exc:
            # Error messages originate only from assertions and sanitized model codes.
            evidence["rows"][str(row)] = {
                "status": "fail",
                "elapsed_seconds": round(time.monotonic() - began, 3),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            print(f"row {row}: FAIL {type(exc).__name__}: {exc}", flush=True)
        save()

    with tempfile.TemporaryDirectory(prefix="starcoach-runtime-qa-") as temporary:
        q = JobQueue(Path(temporary) / "jobs.sqlite3")
        app = FastAPI()
        app.include_router(worker_router(q, token))
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
        server_thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        server_thread.start()
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        assert server.started, "Uvicorn did not start"
        origin = f"http://127.0.0.1:{port}"
        evidence["origin"] = origin

        def observe(response):
            response.read()
            evidence["http"].append(
                {
                    "method": response.request.method,
                    "path": response.request.url.path,
                    "status": response.status_code,
                }
            )
            if response.request.url.path.endswith("/claim") and response.status_code == 200:
                job = response.json().get("job")
                if job:
                    claims[job["id"]] = {key: job[key] for key in ("lease_id", "completion_token")}

        h = httpx.Client(
            base_url=origin,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            event_hooks={"response": [observe]},
        )
        model = CodexCliClient(
            binary=args.binary, auth_file=args.auth_file, image=args.image, gate_dir=args.gate_dir
        )
        evidence["cli_version"] = model.cli_version

        def new_worker():
            worker = PullWorker(origin, token, model, allow_loopback_http=True, poll_seconds=0.2)
            worker.http.event_hooks["response"].append(observe)
            workers.append(worker)
            return worker

        w = new_worker()

        def seed(owner, request=None):
            now = time.time()
            return q.enqueue(
                owner=owner,
                request_id=request or secrets.token_hex(8),
                payload={
                    "fixture-1": "No current quote or verified account. A brief Persian reason is required."
                },
                schema=SCHEMA,
                schema_id="qa-hold",
                prompt_version="1",
                deadline=now + 120,
                now=now,
            )

        def heartbeat():
            assert h.post(PREFIX + "/heartbeat", json={"worker_id": w.worker_id}).status_code == 200

        def completion(job, value=GOOD, **override):
            return h.post(
                PREFIX + f"/jobs/{job['id']}/complete",
                json={**claims[job["id"]], "result": value, **override},
            )

        def state(job, owner):
            return q.get(job["id"], owner, time.time())

        def wait_container(future):
            began = time.monotonic()
            while time.monotonic() - began < 15:
                found = containers() - baseline - observed
                if found:
                    assert len(found) == 1, "Multiple inference containers appeared"
                    cid = next(iter(found))
                    details = json.loads(docker("inspect", cid))[0]
                    assert details["Config"]["Labels"].get("starcoach.model") == "torob"
                    observed.add(cid)
                    evidence["model_starts"] += 1
                    return {
                        "id": cid,
                        "name": details["Name"],
                        "label": LABEL,
                        "read_only": details["HostConfig"]["ReadonlyRootfs"],
                        "cap_drop": details["HostConfig"]["CapDrop"],
                        "container_env_has_worker_token": any(token in v for v in details["Config"]["Env"]),
                        "mount_targets": [m["Destination"] for m in details["Mounts"]],
                    }
                if future.done():
                    raise AssertionError(f"Worker finished before container observation: {future.result()}")
                time.sleep(0.08)
            raise AssertionError("No labeled inference container observed")

        try:

            def auth():
                codes = []
                for headers in ({}, {"Authorization": "Bearer wrong"}, {"Cookie": "session=owner"}):
                    with httpx.Client(base_url=origin, event_hooks={"response": [observe]}) as unauth:
                        codes.append(
                            unauth.post(
                                PREFIX + "/heartbeat", json={"worker_id": "unauthorized"}, headers=headers
                            ).status_code
                        )
                assert codes == [401, 401, 401], codes
                with q.connect() as db:
                    count = db.execute("SELECT count(*) FROM model_workers").fetchone()[0]
                assert count == 0
                return {"codes": codes, "persisted_worker_count": count}

            check(1, auth)

            def bounds():
                r = h.post(PREFIX + "/heartbeat", content=b"x" * 65537)
                assert r.status_code == 413, r.status_code
                return {"bytes": 65537, "http": r.status_code, "model_starts": evidence["model_starts"]}

            check(8, bounds)
            heartbeat()
            validation = seed("validation-owner")
            claim = h.post(PREFIX + "/claim", json={"worker_id": w.worker_id})
            assert claim.status_code == 200

            def isolation():
                codes = [
                    h.post(PREFIX + "/heartbeat", json=body).status_code
                    for body in ({"worker_id": ""}, {"worker_id": "w", "unexpected": 1})
                ]
                codes.append(
                    h.get(PREFIX + f"/jobs/{validation['id']}", params={"worker_id": "foreign"}).status_code
                )
                assert codes == [422, 422, 404], codes
                reads = expect_error(lambda: q.get(validation["id"], "foreign", time.time()), "not_found")
                cancels = expect_error(
                    lambda: q.cancel(validation["id"], "foreign", time.time()), "not_found"
                )
                assert state(validation, "validation-owner")["state"] == "leased"
                return {
                    "http_codes": codes,
                    "foreign_owner_read": reads,
                    "foreign_owner_cancel": cancels,
                    "state": "leased",
                }

            check(9, isolation)

            def invalid_completion():
                codes = [
                    completion(validation, lease_id="wrong").status_code,
                    completion(validation, completion_token="wrong").status_code,
                ]
                assert state(validation, "validation-owner")["state"] == "leased"
                codes.append(completion(validation, {**GOOD, "action": "BUY"}).status_code)
                row = state(validation, "validation-owner")
                assert codes == [409, 409, 422], codes
                assert (
                    row["state"] == "failed"
                    and row["error_code"] == "invalid_output"
                    and row["result"] is None
                )
                return {"http_codes": codes, "stored": row}

            check(10, invalid_completion)

            complete_job = seed("completed-owner")
            future = pool.submit(w.once, stop)
            first_container = wait_container(future)

            def contention():
                second_worker = new_worker()
                busy = expect_error(second_worker.once, "busy")
                same_owner = expect_error(lambda: seed("completed-owner"), "busy")
                waiting = [seed("waiting-a"), seed("waiting-b")]
                full = expect_error(lambda: seed("waiting-c"), "queue_full")
                leased = h.post(PREFIX + "/claim", json={"worker_id": "second-worker"}).json()["job"]
                assert leased is None
                active = containers() - baseline
                assert len(active) == 1
                for job, owner in zip(waiting, ("waiting-a", "waiting-b")):
                    q.cancel(job["id"], owner, time.time())
                return {
                    "second_worker": busy,
                    "same_owner": same_owner,
                    "third_waiting": full,
                    "extra_claim": leased,
                    "active_container_count": len(active),
                }

            check(12, contention)

            def real_roundtrip():
                outcome = future.result(timeout=75)
                row = state(complete_job, "completed-owner")
                assert outcome == "completed" and row["state"] == "completed", (
                    outcome,
                    row["state"],
                    row["error_code"],
                )
                assert row["result"]["action"] == "HOLD"
                assert any("\u0600" <= c <= "\u06ff" for c in row["result"]["reason_fa"])
                assert row["provenance"]["provider"] == "codex_cli" and row["provenance"]["elapsed_ms"] > 0
                assert row["provenance"]["model"] == model.model
                assert (
                    token not in json.dumps(row) and "completion_token" not in row and "token_hash" not in row
                )
                assert not (containers() - baseline)
                assert first_container["read_only"] and not first_container["container_env_has_worker_token"]
                return {
                    "worker_outcome": outcome,
                    "stored": row,
                    "container": first_container,
                    "containers_after": [],
                }

            check(2, real_roundtrip)

            def replay():
                before = state(complete_job, "completed-owner")
                response = completion(complete_job)
                after = state(complete_job, "completed-owner")
                assert response.status_code == 409 and before == after
                return {
                    "http": 409,
                    "original_unchanged": True,
                    "result_sha256": hashlib.sha256(
                        json.dumps(after["result"], sort_keys=True).encode()
                    ).hexdigest(),
                }

            check(3, replay)

            def disconnect():
                time.sleep(46)
                assert not q.available(time.time())
                error = expect_error(lambda: seed("disconnected-owner"), "unavailable")
                row = state(complete_job, "completed-owner")
                assert row["state"] == "completed" and row["result"]["action"] == "HOLD"
                return {
                    "wait_seconds": 46,
                    "available": False,
                    "enqueue_error": error,
                    "existing_result_state": row["state"],
                }

            check(4, disconnect)

            heartbeat()
            expired_job = seed("expiry-owner")

            def expiry():
                time.sleep(16)
                row = state(expired_job, "expiry-owner")
                outcome = w.once()
                assert row["state"] == "expired" and outcome == "idle"
                assert state(expired_job, "expiry-owner")["state"] == "expired"
                return {
                    "wait_seconds": 16,
                    "stored": row,
                    "reconnect_outcome": outcome,
                    "model_starts_unchanged": evidence["model_starts"] == 1,
                }

            check(5, expiry)

            cancel_job = seed("cancel-owner")
            cancel_future = pool.submit(w.once, stop)
            cancel_container = wait_container(cancel_future)

            def cancellation():
                q.cancel(cancel_job["id"], "cancel-owner", time.time())
                outcome = cancel_future.result(timeout=15)
                row = state(cancel_job, "cancel-owner")
                response = completion(cancel_job)
                assert outcome == "canceled" and row["state"] == "canceled", (outcome, row["state"])
                assert response.status_code == 409 and row["result"] is None
                assert not (containers() - baseline)
                return {
                    "worker_outcome": outcome,
                    "stored": row,
                    "late_completion_http": 409,
                    "observed_container": cancel_container,
                    "containers_after": [],
                }

            check(6, cancellation)

            w.close()
            w = new_worker()
            heartbeat()
            recovery = seed("recovery-owner")
            recovery_future = pool.submit(w.once, stop)
            recovery_container = wait_container(recovery_future)

            def reconnect():
                outcome = recovery_future.result(timeout=75)
                row = state(recovery, "recovery-owner")
                assert outcome == "completed" and row["result"]["action"] == "HOLD"
                assert state(expired_job, "expiry-owner")["state"] == "expired"
                return {
                    "worker_outcome": outcome,
                    "stored": row,
                    "container": recovery_container,
                    "old_backlog_state": "expired",
                }

            check(11, reconnect)

            def persistence():
                reopened = JobQueue(q.path)
                stored = [
                    reopened.get(job["id"], owner, time.time())
                    for job, owner in (
                        (complete_job, "completed-owner"),
                        (cancel_job, "cancel-owner"),
                        (expired_job, "expiry-owner"),
                        (validation, "validation-owner"),
                        (recovery, "recovery-owner"),
                    )
                ]
                assert [r["state"] for r in stored] == [
                    "completed",
                    "canceled",
                    "expired",
                    "failed",
                    "completed",
                ]
                assert reopened.claim("restarted-worker", time.time()) is None
                return {"reopened_rows": stored, "restart_claim": None}

            check(7, persistence)
        finally:
            stop.set()
            pool.shutdown(wait=True, cancel_futures=True)
            for worker in workers:
                worker.close()
            h.close()
            server.should_exit = True
            server_thread.join(timeout=10)
            # Only ever remove an observed, labeled container belonging to this run.
            survivors = containers() - baseline
            owned_survivors = survivors & observed
            for cid in owned_survivors:
                info = json.loads(docker("inspect", cid))[0]
                if info["Config"]["Labels"].get("starcoach.model") == "torob":
                    docker("rm", "-f", cid)
            evidence["cleanup"] = {
                "server_stopped": not server_thread.is_alive(),
                "owned_survivors_before_cleanup": sorted(owned_survivors),
                "owned_survivors_after_cleanup": sorted(containers() & observed),
                "unrelated_containers_removed": False,
            }
            evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
            evidence["all_passed"] = (
                len(evidence["rows"]) == 12
                and all(row["status"] == "pass" for row in evidence["rows"].values())
                and evidence["cleanup"]["server_stopped"]
                and not evidence["cleanup"]["owned_survivors_before_cleanup"]
                and not evidence["cleanup"]["owned_survivors_after_cleanup"]
            )
            save()
    return 0 if evidence["all_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--binary",
        type=Path,
        default=os.environ.get("CODEX_BINARY_PATH"),
        required=not os.environ.get("CODEX_BINARY_PATH"),
    )
    parser.add_argument(
        "--auth-file",
        type=Path,
        default=os.environ.get("CODEX_AUTH_FILE"),
        required=not os.environ.get("CODEX_AUTH_FILE"),
    )
    parser.add_argument(
        "--image", default=os.environ.get("CODEX_IMAGE"), required=not os.environ.get("CODEX_IMAGE")
    )
    parser.add_argument("--gate-dir", type=Path, default=Path(f"/tmp/starcoach-codex-{os.getuid()}"))
    parser.add_argument("--evidence", type=Path, default=Path("docs/qa-evidence/model-runtime.json"))
    raise SystemExit(run(parser.parse_args()))
