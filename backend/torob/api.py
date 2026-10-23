import json
import os
import sqlite3
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .catalogue import Catalogue
from .external_actions import build_external_actions
from .agent import AgentService
from .model_jobs import JobQueue
from .session import Store, StoreError
from .types import SearchConstraints
from .worker_api import LimitedRoute, worker_router


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewMission(Input):
    product_id: str = Field(min_length=1, max_length=100)
    mode: Literal["assisted", "simulation"] = "assisted"
    constraints: SearchConstraints


class Revision(Input):
    expected_revision: int = Field(ge=1)


class MissionPatch(Revision):
    constraints: dict | None = None
    selected_product_id: str | None = Field(default=None, max_length=100)
    selected_primary_shop_id: str | None = Field(default=None, max_length=100)


class NewFollowup(Input):
    offer_id: str = Field(min_length=1, max_length=100)


class ObservationPreview(Revision):
    followup_id: str = Field(min_length=1, max_length=100)
    kind: Literal[
        "available",
        "unavailable",
        "no_response",
        "price_change",
        "variant_mismatch",
        "payment_conflict",
        "closed",
    ]
    raw_text: str = Field(default="", max_length=4000)
    price_toman: str | None = None
    effective_visit_date: str | None = None


class CompareInput(Input):
    product_ids: list[str] = Field(min_length=2, max_length=2)
    constraints: SearchConstraints


class TurnInput(Input):
    message: str = Field(min_length=1, max_length=4000)
    kind: Literal["needs", "reply"] = "needs"
    mission_id: str | None = Field(default=None, max_length=100)
    base_revision: int | None = Field(default=None, ge=1)
    followup_id: str | None = Field(default=None, max_length=100)
    constraints: SearchConstraints | None = None


def create_app(
    *,
    catalogue_path=None,
    state_db_path=None,
    session_secret=None,
    worker_token=None,
    public_origin=None,
    frontend_dist=None,
    clock=time.time,
):
    catalogue_path = Path(catalogue_path or os.environ.get("CATALOGUE_DB_PATH", "data/catalogue.sqlite"))
    state_db_path = Path(state_db_path or os.environ.get("STATE_DB_PATH", "data/state.sqlite"))
    session_secret = session_secret or os.environ.get("SESSION_SECRET", "")
    worker_token = worker_token or os.environ.get("MODEL_WORKER_TOKEN", "")
    public_origin = (public_origin or os.environ.get("PUBLIC_ORIGIN", "http://127.0.0.1:8000")).rstrip("/")
    parsed = urlsplit(public_origin)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("PUBLIC_ORIGIN must be an HTTP(S) origin")
    catalogue = None
    if catalogue_path.is_file():
        try:
            candidate = Catalogue(catalogue_path)
            with candidate.connect() as db:
                manifest = db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
                if not manifest or not json.loads(manifest[0]).get("payload_hashes"):
                    raise ValueError("Catalogue manifest unavailable")
                db.execute("SELECT product_id FROM product_search LIMIT 1").fetchone()
            catalogue = candidate
        except (ValueError, sqlite3.Error):
            pass
    store, jobs = Store(state_db_path, session_secret, catalogue), JobQueue(state_db_path)
    app = FastAPI(title="Torob purchase mission", docs_url=None, redoc_url=None)
    app.router.route_class = LimitedRoute
    app.state.store, app.state.jobs, app.state.catalogue = store, jobs, catalogue
    app.state.clock = clock
    agent = AgentService(store, jobs, catalogue, clock)
    app.state.agent = agent
    rates = defaultdict(deque)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        path, now = request.url.path, clock()
        if path.startswith("/api/"):
            ip = request.client.host if request.client else "unknown"
            new_session = path == "/api/sessions"
            if new_session:
                try:
                    store.resolve_session(request.cookies.get("torob_session"), now)
                    new_session = False
                except StoreError:
                    pass
            key = (ip, "session" if new_session else "api")
            bucket = rates[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= (10 if key[1] == "session" else 180):
                return JSONResponse({"detail": "rate_limited"}, status_code=429)
            bucket.append(now)
            if request.method in ("POST", "PATCH", "DELETE") and path != "/api/search":
                if request.headers.get("origin") != public_origin:
                    return JSONResponse({"detail": "origin_not_allowed"}, status_code=403)
            if len(rates) > 2048:
                for old in [k for k, v in rates.items() if not v or v[-1] <= now - 60]:
                    rates.pop(old, None)
        response = await call_next(request)
        if path.startswith(("/api/", "/internal/")):
            response.headers["cache-control"] = "no-store"
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        return response

    @app.exception_handler(StoreError)
    async def store_error(_request, exc):
        return JSONResponse({"detail": exc.code}, status_code=exc.status)

    def ready():
        if catalogue is None:
            raise HTTPException(503, "catalogue_unavailable")
        return catalogue

    def owner(request: Request):
        return store.resolve_session(request.cookies.get("torob_session"), clock())

    def public_mission(mission):
        return mission.model_dump(mode="json", exclude={"session_id"})

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/readyz")
    def readiness(_catalogue=Depends(ready)):
        return {"status": "ready"}

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "catalogue_ready": catalogue is not None,
            "model_available": jobs.available(clock()),
            "model_provider": "codex_cli",
            "seller_contact": "assisted_or_simulated",
        }

    @app.post("/api/sessions")
    def sessions(request: Request, response: Response):
        try:
            store.resolve_session(request.cookies.get("torob_session"), clock())
        except StoreError:
            cookie, _ = store.create_session(clock())
            response.set_cookie(
                "torob_session",
                cookie,
                max_age=86400,
                httponly=True,
                secure=parsed.scheme == "https",
                samesite="strict",
                path="/",
            )
        return {"session": "ready"}

    @app.post("/api/search")
    def search(body: SearchConstraints, source=Depends(ready)):
        products = source.search_products(body)
        return {"products": products, "diagnostics": [] if products else source.search_diagnostics(body)}

    @app.get("/api/locations")
    def locations(q: str = Query(min_length=1, max_length=100), source=Depends(ready)):
        return {"locations": source.search_locations(q), "source": "catalogue_shop_coordinates"}

    @app.post("/api/products/compare")
    def compare(body: CompareInput, source=Depends(ready)):
        try:
            return {"products": source.compare_products(body.product_ids, body.constraints), "constraints": body.constraints}
        except KeyError as exc:
            raise HTTPException(404, "product_not_found") from exc

    @app.get("/api/products/{product_id}")
    def product(product_id: str, source=Depends(ready)):
        try:
            return source.get_product(product_id)
        except KeyError as exc:
            raise HTTPException(404, "product_not_found") from exc

    @app.post("/api/missions", status_code=201)
    def new_mission(body: NewMission, session=Depends(owner), source=Depends(ready)):
        mission = store.create_mission(session, body.product_id, body.constraints, body.mode, clock())
        return {"mission": public_mission(mission), "plan": store.plan(session, mission.id)}

    @app.get("/api/products/{product_id}/offers")
    def offers(product_id: str, constraints: Annotated[SearchConstraints, Query()], source=Depends(ready)):
        try:
            return {"offers": source.find_offers(product_id, constraints)}
        except KeyError as exc:
            raise HTTPException(404, "product_not_found") from exc

    @app.post("/api/turns", status_code=202)
    def start_turn(body: TurnInput, session=Depends(owner), source=Depends(ready)):
        args = body.model_dump(exclude={"message", "constraints"})
        return agent.start_turn(session, body.message, constraints=body.constraints, **args)

    @app.get("/api/turns/{turn_id}")
    def get_turn(turn_id: str, session=Depends(owner), source=Depends(ready)):
        return agent.get_turn(session, turn_id)

    @app.post("/api/turns/{turn_id}/cancel")
    def cancel_turn(turn_id: str, session=Depends(owner)):
        return agent.cancel_turn(session, turn_id)

    @app.get("/api/missions/{mission_id}")
    def mission(mission_id: str, session=Depends(owner), source=Depends(ready)):
        result = store.get_mission(session, mission_id)
        return {
            "mission": public_mission(result),
            "product": source.get_product(result.selected_product_id),
            "plan": store.plan(session, mission_id),
        }

    @app.patch("/api/missions/{mission_id}")
    def patch_mission(mission_id: str, body: MissionPatch, session=Depends(owner), source=Depends(ready)):
        patch = body.model_dump(exclude_unset=True, exclude={"expected_revision"})
        result = store.patch_mission(session, mission_id, body.expected_revision, patch, clock())
        return {"mission": public_mission(result), "plan": store.plan(session, mission_id)}

    @app.get("/api/missions/{mission_id}/plan")
    def plan(mission_id: str, session=Depends(owner), source=Depends(ready)):
        return store.plan(session, mission_id)

    @app.get("/api/missions/{mission_id}/history")
    def history(mission_id: str, session=Depends(owner)):
        return {"events": store.history(session, mission_id)}

    @app.get("/api/missions/{mission_id}/actions")
    def actions(mission_id: str, session=Depends(owner), source=Depends(ready)):
        mission, plan = store.snapshot(session, mission_id)
        product = source.get_product(mission.selected_product_id)
        return {
            "revision": mission.revision,
            "actions": build_external_actions(product, plan.primary, mission),
        }

    @app.post("/api/missions/{mission_id}/followups")
    def followup(mission_id: str, body: NewFollowup, session=Depends(owner), source=Depends(ready)):
        return store.create_followup(session, mission_id, body.offer_id, clock())

    @app.post("/api/missions/{mission_id}/observations/preview")
    def preview(mission_id: str, body: ObservationPreview, session=Depends(owner), source=Depends(ready)):
        fields = body.model_dump(exclude={"followup_id", "expected_revision", "kind"})
        return store.preview_observation(
            session, mission_id, body.followup_id, body.expected_revision, body.kind, now=clock(), **fields
        )

    @app.post("/api/missions/{mission_id}/observations/{observation_id}/confirm")
    def confirm(
        mission_id: str, observation_id: str, body: Revision, session=Depends(owner), source=Depends(ready)
    ):
        plan, delta = store.confirm_observation(
            session, mission_id, observation_id, body.expected_revision, clock()
        )
        return {
            "mission": public_mission(store.get_mission(session, mission_id)),
            "plan": plan,
            "delta": delta,
        }

    @app.post("/api/missions/{mission_id}/reset")
    def reset(mission_id: str, body: Revision, session=Depends(owner), source=Depends(ready)):
        result = store.reset(session, mission_id, body.expected_revision, clock())
        return {"mission": public_mission(result), "plan": store.plan(session, mission_id)}

    app.include_router(worker_router(jobs, worker_token, clock))
    dist = Path(frontend_dist) if frontend_dist else Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
