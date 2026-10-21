import hmac
import time
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .model_jobs import JobQueue
from .model_types import ModelError


class LimitedRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def limited(request: Request):
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 64 * 1024:
                    raise HTTPException(413, "request_too_large")
            request._body = bytes(body)
            return await original(request)

        return limited


class WorkerIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = Field(min_length=1, max_length=100)


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["codex_cli", "omniroute"]
    model: str = Field(min_length=1, max_length=100)
    cli_version: str = Field(max_length=100)
    elapsed_ms: int = Field(ge=0, le=120000)


class Completion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_id: str = Field(min_length=1, max_length=100)
    completion_token: str = Field(min_length=1, max_length=200)
    result: dict
    provenance: Provenance | None = None


class Failure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_id: str = Field(min_length=1, max_length=100)
    completion_token: str = Field(min_length=1, max_length=200)
    error_code: str = Field(min_length=1, max_length=100)


def worker_router(queue: JobQueue, token: str, clock: Callable = time.time):
    if len(token) < 32:
        raise ValueError("Worker secret must have at least 32 characters")

    def authenticate(request: Request):
        value = request.headers.get("authorization", "")
        if not hmac.compare_digest(value, f"Bearer {token}"):
            raise HTTPException(401, "worker_unauthorized")

    router = APIRouter(
        prefix="/internal/model-worker", dependencies=[Depends(authenticate)], route_class=LimitedRoute
    )

    def invoke(fn, *args):
        try:
            return fn(*args)
        except ModelError as exc:
            status = {"not_found": 404, "conflict": 409, "invalid_output": 422}.get(exc.code, 503)
            raise HTTPException(status, exc.code) from exc

    @router.post("/heartbeat")
    def heartbeat(body: WorkerIdentity):
        queue.heartbeat(body.worker_id, clock())
        return {"available": True}

    @router.post("/claim")
    def claim(body: WorkerIdentity):
        return {"job": queue.claim(body.worker_id, clock())}

    @router.get("/jobs/{job_id}")
    def status(job_id: str, worker_id: str):
        return invoke(queue.worker_status, job_id, worker_id, clock())

    @router.post("/jobs/{job_id}/complete")
    def complete(job_id: str, body: Completion):
        return invoke(
            queue.complete,
            job_id,
            body.lease_id,
            body.completion_token,
            body.result,
            clock(),
            body.provenance.model_dump() if body.provenance else None,
        )

    @router.post("/jobs/{job_id}/fail")
    def fail(job_id: str, body: Failure):
        invoke(queue.fail, job_id, body.lease_id, body.completion_token, body.error_code, clock())
        return {"state": "failed"}

    return router
