"""Isolated real HTTP/domain QA with a deterministic fixture worker; NO model calls."""

import sys
import threading
import time
import tempfile
from pathlib import Path

import uvicorn

root = Path(__file__).resolve().parents[1]


def fixture_application():
    sys.path.insert(0, str(root / "backend"))
    from torob.api import create_app

    return create_app(
        catalogue_path=root / "data/catalogue.sqlite",
        state_db_path=Path(tempfile.gettempdir()) / "torob-discovery-fixture.sqlite",
        session_secret="controlled-discovery-fixture-session-secret-32-chars",
        worker_token="controlled-discovery-fixture-worker-secret-32-chars",
        public_origin="http://127.0.0.1:8672",
        frontend_dist=root / "frontend/dist",
    )


app = fixture_application()


def worker():
    last = 0
    while True:
        now = time.time()
        if now - last > 3:
            app.state.jobs.heartbeat("controlled-fixture", now)
            last = now
        job = app.state.jobs.claim("controlled-fixture", now)
        if job:
            payload = job["payload"]
            if job["schema_id"].startswith("torob-needs"):
                context = payload.get("discovery_context")
                value = {
                    "action": "search",
                    "comparison_queries": [],
                    "query": "A07",
                    "category": "گوشی موبایل",
                    "max_price_toman": payload["current_constraints"]["max_price_toman"],
                    "clarification_fa": None,
                    "condition_changes": None,
                }
                if context:
                    value["reference_product_ids"] = []
                    if "مقایسه" in payload["message"]:
                        value.update(
                            action="compare",
                            comparison_queries=[],
                            reference_product_ids=[p["product_id"] for p in context["products"][:2]][::-1],
                        )
            elif job["schema_id"] == "torob-explain-v1":
                value = {
                    "recommendations": [
                        {
                            "product_id": p["product_id"],
                            "reason_fa": "این گزینه از داده ثبت‌شده قابل بررسی است.",
                            "fact_ids": [p["facts"][0]["id"]],
                        }
                        for p in payload["candidates"][:2]
                    ]
                }
            else:
                app.state.jobs.fail(
                    job["id"], job["lease_id"], job["completion_token"], "unexpected_fixture_job", time.time()
                )
                continue
            app.state.jobs.complete(
                job["id"],
                job["lease_id"],
                job["completion_token"],
                value,
                time.time(),
                {
                    "provider": "codex_cli",
                    "model": "controlled-no-model-fixture",
                    "cli_version": "fixture",
                    "elapsed_ms": 1,
                },
            )
        time.sleep(0.1)


threading.Thread(target=worker, daemon=True).start()
uvicorn.run(app, host="127.0.0.1", port=8672, log_level="warning")
