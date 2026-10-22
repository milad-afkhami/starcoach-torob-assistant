import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .followup import KINDS, active_observations, compare_plans, dimension
from .types import Mission, SearchConstraints


class StoreError(RuntimeError):
    def __init__(self, code, status=422):
        self.code, self.status = code, status
        super().__init__(code)


class Store:
    def __init__(self, path: Path, secret: str, catalogue):
        if len(secret) < 32:
            raise ValueError("Session signing secret must be at least32 characters")
        self.path, self.secret, self.catalogue = Path(path), secret.encode(), catalogue
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,expires REAL);
              CREATE TABLE IF NOT EXISTS missions(id TEXT PRIMARY KEY,owner TEXT,revision INTEGER,data TEXT);
              CREATE TABLE IF NOT EXISTS followups(id TEXT PRIMARY KEY,mission_id TEXT,data TEXT);
              CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,mission_id TEXT,confirmed INTEGER,
                applied_revision INTEGER,data TEXT);
              CREATE TABLE IF NOT EXISTS mission_events(id TEXT PRIMARY KEY,mission_id TEXT,revision INTEGER,
                created REAL,data TEXT);
              CREATE INDEX IF NOT EXISTS observations_mission ON observations(mission_id,applied_revision);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _signature(self, session_id):
        return hmac.new(self.secret, session_id.encode(), hashlib.sha256).hexdigest()

    def create_session(self, now):
        session_id = secrets.token_urlsafe(24)
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES(?,?)", (session_id, now + 86400))
        return session_id + "." + self._signature(session_id), session_id

    def resolve_session(self, cookie, now):
        if not isinstance(cookie, str) or len(cookie) > 200 or "." not in cookie:
            raise StoreError("unauthenticated", 401)
        session_id, signature = cookie.split(".", 1)
        if not hmac.compare_digest(signature.encode(), self._signature(session_id).encode()):
            raise StoreError("unauthenticated", 401)
        with self.connect() as db:
            row = db.execute("SELECT expires FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None or row[0] <= now:
            raise StoreError("session_expired", 401)
        return session_id

    def _mission(self, db, owner, mission_id):
        row = db.execute("SELECT data FROM missions WHERE id=? AND owner=?", (mission_id, owner)).fetchone()
        if row is None:
            raise StoreError("not_found", 404)
        return Mission.model_validate_json(row[0])

    def get_mission(self, owner, mission_id):
        with self.connect() as db:
            return self._mission(db, owner, mission_id)

    @staticmethod
    def _revision(mission, expected):
        if mission.revision != expected:
            raise StoreError("stale_revision", 409)

    def _product(self, product_id):
        try:
            return self.catalogue.get_product(product_id)
        except KeyError as exc:
            raise StoreError("product_not_found", 404) from exc

    def create_mission(self, owner, product_id, constraints, mode, now):
        self._product(product_id)
        try:
            mission = Mission(
                id=uuid.uuid4().hex,
                session_id=owner,
                selected_product_id=product_id,
                constraints=constraints,
                mode=mode,
            )
        except ValidationError as exc:
            raise StoreError("invalid_mission") from exc
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM sessions WHERE id=? AND expires>?", (owner, now)).fetchone():
                raise StoreError("unauthenticated", 401)
            db.execute(
                "INSERT INTO missions VALUES(?,?,?,?)", (mission.id, owner, 1, mission.model_dump_json())
            )
        return mission

    def patch_mission(self, owner, mission_id, expected_revision, patch, now):
        if set(patch) - {"constraints", "selected_product_id", "selected_primary_shop_id"}:
            raise StoreError("invalid_mission_patch")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            mission = self._mission(db, owner, mission_id)
            self._revision(mission, expected_revision)
            data = mission.model_dump(mode="json")
            try:
                if "constraints" in patch:
                    data["constraints"].update(patch["constraints"])
                    data["constraints"] = SearchConstraints.model_validate(data["constraints"]).model_dump(
                        mode="json"
                    )
                if "selected_product_id" in patch:
                    self._product(patch["selected_product_id"])
                    data["selected_product_id"] = patch["selected_product_id"]
                    data["selected_primary_shop_id"] = None
                if "selected_primary_shop_id" in patch:
                    data["selected_primary_shop_id"] = patch["selected_primary_shop_id"]
                data["revision"] += 1
                updated = Mission.model_validate(data)
            except (TypeError, ValueError) as exc:
                raise StoreError("invalid_mission_patch") from exc
            db.execute(
                "UPDATE missions SET revision=?,data=? WHERE id=?",
                (updated.revision, updated.model_dump_json(), mission_id),
            )
            return updated

    @staticmethod
    def _observations(db, mission_id):
        return [
            json.loads(r[0])
            for r in db.execute(
                "SELECT data FROM observations WHERE mission_id=? AND confirmed=1 ORDER BY applied_revision",
                (mission_id,),
            )
        ]

    def observations(self, owner, mission_id):
        with self.connect() as db:
            self._mission(db, owner, mission_id)
            return self._observations(db, mission_id)

    def plan(self, owner, mission_id):
        return self.snapshot(owner, mission_id)[1]

    def snapshot(self, owner, mission_id):
        with self.connect() as db:
            db.execute("BEGIN")
            mission = self._mission(db, owner, mission_id)
            observations = self._observations(db, mission_id)
        return mission, self.catalogue.plan_mission(mission, observations)

    def _offer(self, mission, offer_id):
        offers = self.catalogue.find_offers(mission.selected_product_id, mission.constraints)
        offer = next((o for o in offers if o.offer_id == offer_id), None)
        if offer is None:
            raise StoreError("offer_not_in_mission", 404)
        return offer

    def create_followup(self, owner, mission_id, offer_id, now):
        with self.connect() as db:
            mission = self._mission(db, owner, mission_id)
            offer = self._offer(mission, offer_id)
            product = self._product(mission.selected_product_id)
            inquiry = f"آیا «{product.title or 'کالای انتخاب‌شده'}» با همین مشخصات موجود است؟ قیمت نهایی به تومان چقدر است؟"
            if mission.constraints.visit_at:
                inquiry += f" برای مراجعه در {mission.constraints.visit_at.isoformat()} باز هستید؟"
            if mission.constraints.payment_provider:
                inquiry += f" خرید حضوری این کالا با {mission.constraints.payment_provider} چه شرایطی دارد؟"
            value = {
                "id": uuid.uuid4().hex,
                "mission_id": mission_id,
                "offer_id": offer_id,
                "shop_id": offer.shop_id,
                "product_id": offer.product_id,
                "state": "draft",
                "provenance": "simulation" if mission.mode == "simulation" else "user_reported",
                "inquiry": inquiry,
                "created_at": now,
                "contact_links": offer.contact_links,
            }
            db.execute(
                "INSERT INTO followups VALUES(?,?,?)",
                (value["id"], mission_id, json.dumps(value, ensure_ascii=False)),
            )
            return value

    def preview_observation(
        self,
        owner,
        mission_id,
        followup_id,
        expected_revision,
        kind,
        *,
        raw_text,
        now,
        price_toman=None,
        effective_visit_date=None,
    ):
        if kind not in KINDS or not isinstance(raw_text, str) or len(raw_text) > 4000:
            raise StoreError("invalid_observation")
        if kind == "price_change":
            try:
                value = SearchConstraints(max_price_toman=price_toman).max_price_toman
                if value is None:
                    raise ValueError()
            except ValueError as exc:
                raise StoreError("invalid_quote") from exc
        elif price_toman is not None:
            raise StoreError("unexpected_quote")
        if kind == "closed":
            try:
                effective_visit_date = date.fromisoformat(effective_visit_date).isoformat()
            except (ValueError, TypeError) as exc:
                raise StoreError("closure_date_required") from exc
        elif effective_visit_date is not None:
            raise StoreError("unexpected_closure_date")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            mission = self._mission(db, owner, mission_id)
            self._revision(mission, expected_revision)
            row = db.execute(
                "SELECT data FROM followups WHERE id=? AND mission_id=?", (followup_id, mission_id)
            ).fetchone()
            if row is None:
                raise StoreError("followup_not_found", 404)
            followup = json.loads(row[0])
            offer = self._offer(mission, followup["offer_id"])
            if kind == "payment_conflict" and not mission.constraints.payment_provider:
                raise StoreError("payment_requirement_missing")
            observation = {
                "id": uuid.uuid4().hex,
                "mission_id": mission_id,
                "followup_id": followup_id,
                "offer_id": offer.offer_id,
                "shop_id": offer.shop_id,
                "product_id": offer.product_id,
                "base_revision": mission.revision,
                "scope": "shop_date"
                if kind == "closed"
                else "offer"
                if kind in ("price_change", "variant_mismatch")
                else "product_shop",
                "kind": kind,
                "price_toman": price_toman,
                "effective_visit_date": effective_visit_date,
                "raw_text": raw_text,
                "provenance": "simulation" if mission.mode == "simulation" else "user_reported",
                "payment_provider": mission.constraints.payment_provider
                if kind == "payment_conflict"
                else None,
                "observed_at": now,
                "confirmed_at": None,
                "applied_revision": None,
                "confirmed": False,
                "supersedes_ids": [],
            }
            observation["supersedes_ids"] = [
                o["id"]
                for o in active_observations(self._observations(db, mission_id))
                if dimension(o) == dimension(observation)
            ]
            db.execute(
                "INSERT INTO observations VALUES(?,?,0,NULL,?)",
                (observation["id"], mission_id, json.dumps(observation, ensure_ascii=False)),
            )
            return observation

    def confirm_observation(self, owner, mission_id, observation_id, expected_revision, now):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            mission = self._mission(db, owner, mission_id)
            self._revision(mission, expected_revision)
            row = db.execute(
                "SELECT data FROM observations WHERE id=? AND mission_id=?", (observation_id, mission_id)
            ).fetchone()
            if row is None:
                raise StoreError("observation_not_found", 404)
            obs = json.loads(row[0])
            provenance = "simulation" if mission.mode == "simulation" else "user_reported"
            if obs["confirmed"] or obs["base_revision"] != mission.revision:
                raise StoreError("stale_observation", 409)
            if obs["provenance"] != provenance or obs["mission_id"] != mission_id:
                raise StoreError("observation_scope_mismatch", 409)
            observations = self._observations(db, mission_id)
            index = {o["id"]: o for o in observations}
            if any(
                old not in index
                or dimension(index[old]) != dimension(obs)
                or index[old]["provenance"] != provenance
                for old in obs["supersedes_ids"]
            ):
                raise StoreError("invalid_supersession", 409)
            before = self.catalogue.plan_mission(mission, observations)
            updated = mission.model_copy(update={"revision": mission.revision + 1})
            obs.update(confirmed=True, confirmed_at=now, applied_revision=updated.revision)
            after = self.catalogue.plan_mission(updated, [*observations, obs])
            delta = compare_plans(before, after, mission.constraints, obs["kind"])
            db.execute(
                "UPDATE observations SET confirmed=1,applied_revision=?,data=? WHERE id=?",
                (updated.revision, json.dumps(obs, ensure_ascii=False), observation_id),
            )
            db.execute(
                "UPDATE missions SET revision=?,data=? WHERE id=?",
                (updated.revision, updated.model_dump_json(), mission_id),
            )
            db.execute(
                "INSERT INTO mission_events VALUES(?,?,?,?,?)",
                (uuid.uuid4().hex, mission_id, updated.revision, now, delta.model_dump_json()),
            )
            return after, delta

    def history(self, owner, mission_id):
        with self.connect() as db:
            self._mission(db, owner, mission_id)
            return [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT data FROM mission_events WHERE mission_id=? ORDER BY revision DESC LIMIT 20",
                    (mission_id,),
                )
            ]

    def reset(self, owner, mission_id, expected_revision, now):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            mission = self._mission(db, owner, mission_id)
            if mission.mode != "simulation":
                raise StoreError("simulation_only", 403)
            self._revision(mission, expected_revision)
            updated = mission.model_copy(
                update={"revision": mission.revision + 1, "selected_primary_shop_id": None}
            )
            for table in ("observations", "followups", "mission_events"):
                db.execute(f"DELETE FROM {table} WHERE mission_id=?", (mission_id,))
            db.execute(
                "UPDATE missions SET revision=?,data=? WHERE id=?",
                (updated.revision, updated.model_dump_json(), mission_id),
            )
            return updated
