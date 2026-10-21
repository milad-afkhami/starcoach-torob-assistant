"""Outbound-only worker. Its bearer token never enters the model container."""

import ipaddress
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from urllib.parse import urlsplit

import httpx

from .model_types import ModelError, ModelRequest


class PullWorker:
    def __init__(self, base_url, token, model, *, allow_loopback_http=False, transport=None, poll_seconds=2):
        url = urlsplit(base_url)
        try:
            loopback = ipaddress.ip_address(url.hostname or "").is_loopback
        except ValueError:
            loopback = url.hostname == "localhost"
        if url.scheme != "https" and not (allow_loopback_http and url.scheme == "http" and loopback):
            raise ValueError("Worker requires HTTPS, except explicit loopback test mode")
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise ValueError("Worker base must be one origin without credentials or parameters")
        if len(token) < 32:
            raise ValueError("Worker token must have at least 32 characters")
        self.http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            follow_redirects=False,
            transport=transport,
        )
        self.model, self.poll_seconds = model, poll_seconds
        self.worker_id = "local-" + uuid.uuid4().hex

    def close(self):
        self.http.close()

    def request(self, method, path, body=None, *, expected_conflict=False):
        with self.http.stream(method, "/internal/model-worker" + path, json=body) as response:
            if expected_conflict and response.status_code == 409:
                return {"state": "rejected"}
            response.raise_for_status()
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > 64 * 1024:
                    raise ModelError("oversized_input")
            return json.loads(raw)

    def once(self, stop=None):
        self.request("POST", "/heartbeat", {"worker_id": self.worker_id})
        # Reservation is acquired before claiming work, but charges only on CLI start.
        with self.model.gate.reserve() as permit:
            job = self.request("POST", "/claim", {"worker_id": self.worker_id})["job"]
            if job is None:
                return "idle"
            job_id = job["id"]
            credentials = {"lease_id": job["lease_id"], "completion_token": job["completion_token"]}
            cancel = threading.Event()
            request = ModelRequest(
                id=job_id,
                schema_id=job["schema_id"],
                schema_version="1",
                prompt_version=job["prompt_version"],
                evidence_ids=[],
                payload=job["payload"],
                deadline_utc=min(job["expires"], time.time() + 60),
            )
            last_heartbeat = time.monotonic()
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.model.generate, request, job["schema"], cancel, permit=permit)
                    try:
                        while True:
                            try:
                                result = future.result(timeout=self.poll_seconds)
                                break
                            except TimeoutError:
                                if stop is not None and stop.is_set():
                                    cancel.set()
                                status = self.request("GET", f"/jobs/{job_id}?worker_id={self.worker_id}")
                                if status["state"] != "leased" or request.deadline_utc <= time.time():
                                    cancel.set()
                                if time.monotonic() - last_heartbeat >= 15:
                                    self.request("POST", "/heartbeat", {"worker_id": self.worker_id})
                                    last_heartbeat = time.monotonic()
                    finally:
                        if not future.done():
                            cancel.set()
                accepted = self.request(
                    "POST",
                    f"/jobs/{job_id}/complete",
                    {
                        **credentials,
                        "result": result.value,
                        "provenance": result.model_dump(exclude={"value", "request_id"}),
                    },
                    expected_conflict=True,
                )
                return "completed" if accepted.get("state") == "completed" else "discarded"
            except ModelError as exc:
                self.request(
                    "POST",
                    f"/jobs/{job_id}/fail",
                    {**credentials, "error_code": exc.code},
                    expected_conflict=True,
                )
                return exc.code

    def run(self, stop: threading.Event):
        backoff = 1
        try:
            while not stop.is_set():
                try:
                    outcome = self.once(stop)
                    backoff = 1
                    if outcome == "idle":
                        stop.wait(1)
                except ModelError:
                    stop.wait(2)
                except (httpx.HTTPError, ValueError, KeyError):
                    stop.wait(backoff)
                    backoff = min(30, backoff * 2)
        finally:
            self.close()
