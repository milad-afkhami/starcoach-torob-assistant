"""Isolated real HTTP/domain QA with a deterministic fixture worker; NO model calls."""

import sys
import os
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
        state_db_path=Path(tempfile.gettempdir())
        / os.environ.get("TOROB_FIXTURE_STATE", "torob-discovery-fixture.sqlite"),
        session_secret="controlled-discovery-fixture-session-secret-32-chars",
        worker_token="controlled-discovery-fixture-worker-secret-32-chars",
        public_origin=f"http://127.0.0.1:{os.environ.get('TOROB_FIXTURE_PORT', '8672')}",
        frontend_dist=Path(os.environ.get("TOROB_FIXTURE_DIST", str(root / "frontend/dist"))),
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
                    "semantic_requirements": [],
                    "spec_focus_terms": [],
                    "comparison_queries": [],
                    "query": "A07",
                    "category": "گوشی موبایل",
                    "max_price_toman": payload["current_constraints"]["max_price_toman"],
                    "clarification_fa": None,
                    "condition_changes": None,
                }
                if "بدون نتیجه" in payload["message"]:
                    value.update(query="zzfixture_not_in_cataloguezz", category=None)
                if payload["message"].strip() == "کمکم کن":
                    value.update(
                        action="clarify",
                        query="",
                        category=None,
                        clarification_fa="چه کالایی می‌خواهی؟ نام یا کاربرد و بودجه‌ات را بگو.",
                    )
                semantic = payload.get("semantic_context") or {}
                if semantic.get("requirements"):
                    value.update(
                        query=payload["current_constraints"]["query"],
                        category=payload["current_constraints"]["category"],
                    )
                if "دانشگاه" in payload["message"] and "نزدیک انقلاب" in payload["message"]:
                    value.update(
                        action="clarify",
                        query="لپ تاپ",
                        category="لپ تاپ و نوت بوک",
                        max_price_toman="60000000",
                        clarification_fa="مبدأ نزدیک انقلاب را از نشانی ثبت‌شده انتخاب کن.",
                        semantic_requirements=[
                            {
                                "label_fa": "نزدیک انقلاب",
                                "source_quote": "نزدیک انقلاب",
                                "kind": "location",
                                "hard": True,
                                "spec_terms": [],
                                "numeric": None,
                            }
                        ],
                    )
                if "وزن کمتر از 1.5 کیلوگرم" in payload["message"]:
                    value.update(
                        query="لپ تاپ",
                        category="لپ تاپ و نوت بوک",
                        max_price_toman="45000000",
                        spec_focus_terms=["وزن"],
                        semantic_requirements=[
                            {
                                "label_fa": "وزن کمتر از 1.5 کیلوگرم",
                                "source_quote": "وزن کمتر از 1.5 کیلوگرم",
                                "kind": "spec",
                                "hard": True,
                                "spec_terms": ["وزن"],
                                "numeric": {"operator": "lt", "value": "1.5", "unit": "kg"},
                            }
                        ],
                    )
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


if not os.environ.get("TOROB_FIXTURE_NO_WORKER"):
    threading.Thread(target=worker, daemon=True).start()
uvicorn.run(
    app, host="127.0.0.1", port=int(os.environ.get("TOROB_FIXTURE_PORT", "8672")), log_level="warning"
)
