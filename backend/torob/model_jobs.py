"""Short SQLite transactions for one active worker and two waiting requests."""

import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .codex_cli import validate_schema
from .model_types import ModelError


class JobQueue:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS model_workers(id TEXT PRIMARY KEY, seen REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS model_requests(
                  owner TEXT, id TEXT, created REAL, deadline REAL, calls INTEGER,
                  PRIMARY KEY(owner,id));
                CREATE TABLE IF NOT EXISTS model_jobs(
                  id TEXT PRIMARY KEY, owner TEXT, request_id TEXT, mission_id TEXT, revision INTEGER,
                  state TEXT, created REAL, expires REAL, claim_by REAL,
                  worker TEXT, lease_id TEXT, lease_expires REAL, token_hash TEXT,
                  payload TEXT, schema_json TEXT, schema_id TEXT, prompt_version TEXT,
                  result TEXT, error_code TEXT);
                CREATE INDEX IF NOT EXISTS job_states ON model_jobs(state,created);
            """)
            if "provenance" not in {r[1] for r in db.execute("PRAGMA table_info(model_jobs)")}:
                db.execute("ALTER TABLE model_jobs ADD COLUMN provenance TEXT")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _expire(db, now):
        db.execute(
            """UPDATE model_jobs SET state='expired', error_code='expired'
            WHERE (state='queued' AND claim_by<=?) OR
                  (state='leased' AND (lease_expires<=? OR expires<=?))""",
            (now, now, now),
        )
        # Keep counts/state, not old raw user inputs/results.
        db.execute("UPDATE model_jobs SET payload='{}',result=NULL WHERE created<?", (now - 86400,))

    def expire(self, now):
        with self.connect() as db:
            before = db.total_changes
            self._expire(db, now)
            return db.total_changes - before

    def heartbeat(self, worker, now):
        with self.connect() as db:
            db.execute(
                "INSERT INTO model_workers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET seen=excluded.seen",
                (worker, now),
            )

    def available(self, now):
        with self.connect() as db:
            seen = db.execute("SELECT MAX(seen) FROM model_workers").fetchone()[0]
            return seen is not None and now - seen < 45

    @staticmethod
    def _public(row):
        result = dict(row)
        for key in ("token_hash", "schema_json", "payload", "worker", "owner"):
            result.pop(key, None)
        result["result"] = json.loads(result["result"]) if result.get("result") else None
        result["provenance"] = json.loads(result["provenance"]) if result.get("provenance") else None
        return result

    def enqueue(
        self,
        *,
        owner,
        request_id,
        payload,
        schema,
        schema_id,
        prompt_version,
        deadline,
        now,
        mission_id=None,
        revision=None,
    ):
        import math

        if not math.isfinite(deadline) or deadline <= now:
            raise ModelError("expired")
        raw = json.dumps(payload, ensure_ascii=False)
        if len(raw.encode()) > 48 * 1024:
            raise ModelError("oversized_input")
        validate_schema(schema)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._expire(db, now)
            seen = db.execute("SELECT MAX(seen) FROM model_workers").fetchone()[0]
            if seen is None or now - seen >= 45:
                raise ModelError("unavailable")
            if db.execute(
                "SELECT 1 FROM model_jobs WHERE owner=? AND state IN ('queued','leased')", (owner,)
            ).fetchone():
                raise ModelError("busy")
            waiting = db.execute("SELECT COUNT(*) FROM model_jobs WHERE state='queued'").fetchone()[0]
            if waiting >= 2:
                raise ModelError("queue_full")
            previous = db.execute(
                "SELECT * FROM model_requests WHERE owner=? AND id=?", (owner, request_id)
            ).fetchone()
            if previous:
                if previous["calls"] >= 2:
                    raise ModelError("request_call_limit")
                deadline = min(deadline, previous["deadline"])
                if deadline <= now:
                    raise ModelError("expired")
                db.execute(
                    "UPDATE model_requests SET calls=calls+1 WHERE owner=? AND id=?", (owner, request_id)
                )
            else:
                count = db.execute(
                    "SELECT COUNT(*) FROM model_requests WHERE owner=? AND created>?", (owner, now - 3600)
                ).fetchone()[0]
                if count >= 10:
                    raise ModelError("rate_limited")
                deadline = min(deadline, now + 120)
                db.execute("INSERT INTO model_requests VALUES(?,?,?,?,1)", (owner, request_id, now, deadline))
            job_id = uuid.uuid4().hex
            db.execute(
                """INSERT INTO model_jobs(id,owner,request_id,mission_id,revision,state,created,expires,
                        claim_by,payload,schema_json,schema_id,prompt_version)
                        VALUES(?,?,?,?,?,'queued',?,?,?,?,?,?,?)""",
                (
                    job_id,
                    owner,
                    request_id,
                    mission_id,
                    revision,
                    now,
                    deadline,
                    min(deadline, now + 15),
                    raw,
                    json.dumps(schema),
                    schema_id,
                    prompt_version,
                ),
            )
            return self._public(db.execute("SELECT * FROM model_jobs WHERE id=?", (job_id,)).fetchone())

    def claim(self, worker, now):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._expire(db, now)
            if db.execute("SELECT 1 FROM model_jobs WHERE state='leased'").fetchone():
                return None
            row = db.execute(
                "SELECT * FROM model_jobs WHERE state='queued' ORDER BY created,rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            token, lease = secrets.token_urlsafe(32), uuid.uuid4().hex
            until = min(row["expires"], now + 65)
            db.execute(
                """UPDATE model_jobs SET state='leased',worker=?,lease_id=?,lease_expires=?,token_hash=?
                       WHERE id=?""",
                (worker, lease, until, hashlib.sha256(token.encode()).hexdigest(), row["id"]),
            )
            result = self._public(db.execute("SELECT * FROM model_jobs WHERE id=?", (row["id"],)).fetchone())
            return {
                **result,
                "completion_token": token,
                "payload": json.loads(row["payload"]),
                "schema": json.loads(row["schema_json"]),
            }

    def get(self, job_id, owner, now):
        with self.connect() as db:
            self._expire(db, now)
            row = db.execute("SELECT * FROM model_jobs WHERE id=? AND owner=?", (job_id, owner)).fetchone()
            if row is None:
                raise ModelError("not_found")
            return self._public(row)

    def worker_status(self, job_id, worker, now):
        with self.connect() as db:
            self._expire(db, now)
            row = db.execute("SELECT * FROM model_jobs WHERE id=? AND worker=?", (job_id, worker)).fetchone()
            if row is None:
                raise ModelError("not_found")
            return {"id": row["id"], "state": row["state"], "expires": row["expires"]}

    def cancel(self, job_id, owner, now):
        with self.connect() as db:
            self._expire(db, now)
            row = db.execute(
                "SELECT state FROM model_jobs WHERE id=? AND owner=?", (job_id, owner)
            ).fetchone()
            if row is None:
                raise ModelError("not_found")
            if row["state"] in ("queued", "leased"):
                db.execute(
                    "UPDATE model_jobs SET state='canceled',error_code='canceled' WHERE id=?", (job_id,)
                )

    def _leased(self, db, job_id, lease, token, now):
        self._expire(db, now)
        row = db.execute("SELECT * FROM model_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None or row["state"] != "leased" or row["lease_id"] != lease:
            raise ModelError("conflict")
        if not hmac.compare_digest(row["token_hash"], hashlib.sha256(token.encode()).hexdigest()):
            raise ModelError("conflict")
        return row

    def complete(self, job_id, lease, token, value, now, provenance=None):
        invalid = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._leased(db, job_id, lease, token, now)
            raw = json.dumps(value, ensure_ascii=False)
            try:
                if len(raw.encode()) > 16 * 1024:
                    raise ValueError()
                Draft202012Validator(json.loads(row["schema_json"])).validate(value)
            except (ValueError, ValidationError):
                db.execute(
                    "UPDATE model_jobs SET state='failed',error_code='invalid_output' WHERE id=?", (job_id,)
                )
                invalid = True
            else:
                db.execute(
                    "UPDATE model_jobs SET state='completed',result=?,provenance=? WHERE id=?",
                    (raw, json.dumps(provenance) if provenance else None, job_id),
                )
            result = self._public(db.execute("SELECT * FROM model_jobs WHERE id=?", (job_id,)).fetchone())
        if invalid:
            raise ModelError("invalid_output")
        return result

    def fail(self, job_id, lease, token, code, now):
        allowed = {
            "canceled",
            "timeout",
            "provider_failed",
            "invalid_output",
            "expired",
            "busy",
            "budget_exhausted",
            "missing_output",
            "oversized_output",
            "runtime_unavailable",
        }
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._leased(db, job_id, lease, token, now)
            db.execute(
                "UPDATE model_jobs SET state='failed',error_code=? WHERE id=?",
                (code if code in allowed else "provider_failed", job_id),
            )
