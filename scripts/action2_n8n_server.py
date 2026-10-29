"""Temporary one-shot, budget-guarded entry point for the real n8n evaluation.

Run one worker only, with the normal backend image and persistent data mount.
The normal production process must be stopped first. Never auto-restart this
entry point after admission; inspect the marker and saved run instead.
"""
import asyncio
import hashlib
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_budget import EvaluationBudget

QUESTION = "How do FDA and USDA divide federal oversight of cell-cultivated chicken for human food in the United States, and what does FDA pre-market consultation establish versus not establish?"
SOURCE_URLS = [
    "https://www.fda.gov/food/food-ingredients-packaging/human-food-made-cultured-animal-cells",
    "https://www.fsis.usda.gov/policy/fsis-directives/7800.1",
]
PAYLOAD = {"question": QUESTION, "source_urls": SOURCE_URLS, "max_rounds": 2}


class OneShotGuard:
    def __init__(self, root, max_new_reservation="1.10"):
        self.root = Path(root)
        self.marker = self.root / "action2-admitted.json"
        self.initial = EvaluationBudget(self.root / "budget.json")
        self.initial_reserved = self.initial.reserved
        self.run_limit = self.initial_reserved + Decimal(max_new_reservation)
        if self.initial.cap != Decimal("3.50"):
            raise RuntimeError("Expected preserved $3.50 reservation stop")
        if self.initial.cap - self.initial_reserved < Decimal("0.80"):
            raise RuntimeError("Insufficient capacity for planned evaluation")
        if self.marker.exists():
            raise RuntimeError("Already admitted; inspect existing run, never relaunch")

    def event(self, **data):
        with (self.root / "action2-transport.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": time.time(), **data}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def reserve(self, kind, kwargs=None):
        # The process lock spans the server lifetime. Reload rather than relying
        # on a stale in-memory ledger. Never refund or reset old reservations.
        if not self.marker.exists():
            raise RuntimeError("No admitted evaluation; paid request blocked")
        budget = EvaluationBudget(self.root / "budget.json")
        if budget.entries[:len(self.initial.entries)] != self.initial.entries:
            raise RuntimeError("Prior reservation history changed")
        if kind == "mesh":
            messages = json.dumps(kwargs["messages"], ensure_ascii=False).encode("utf-8")
            amount = (Decimal(len(messages) + 8192) + Decimal(kwargs["max_tokens"]) * 5) / 1000000
        else:
            amount = Decimal("0.01")
        if budget.reserved + amount > self.run_limit:
            self.event(kind=kind, event="blocked_before_dispatch", reason="run_reservation_limit")
            raise RuntimeError("Evaluation per-run reservation exhausted before sending request")
        if kind == "mesh":
            budget.reserve_mesh(kwargs)
        else:
            budget.reserve_search()
        self.event(kind=kind, event="reserved", cumulative_reserved_usd=str(budget.reserved))

    def admit(self, payload):
        from app.models.schemas import ResearchRequest
        request = ResearchRequest.model_validate(payload)
        if (request.question != QUESTION or request.source_urls != SOURCE_URLS
                or request.max_rounds != 2 or request.confidence_threshold not in (None, 0.7)):
            raise ValueError("Only the approved bounded evaluation is permitted")
        with self.marker.open("x", encoding="utf-8") as stream:
            json.dump({"payload": PAYLOAD, "prior_reserved_usd": str(self.initial_reserved),
                       "planned_reservation_usd": "0.80", "max_new_reservation_usd": "1.10",
                       "billing_verified": False, "admitted_at": time.time()}, stream)
            stream.flush()
            os.fsync(stream.fileno())

    async def mesh_create(self, real_create, **kwargs):
        self.reserve("mesh", kwargs)
        key = hashlib.sha256(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()
        self.event(kind="mesh", event="dispatch_attempt", request_hash=key)
        start = time.monotonic()
        try:
            response = await real_create(**kwargs)
        except BaseException as exc:
            self.event(kind="mesh", event="transport_error", error_type=type(exc).__name__)
            raise
        self.event(kind="mesh", event="response", request_hash=key,
                   duration_ms=int((time.monotonic() - start) * 1000))
        return response

    async def search(self, real_search, query):
        self.reserve("brave")
        self.event(kind="brave", event="dispatch_attempt")
        return await real_search(query)


def install_admission(app, guard):
    from starlette.responses import JSONResponse

    @app.middleware("http")
    async def admission(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.method != "POST" or request.url.path != "/research":
                return JSONResponse({"detail": "Evaluation maintenance: research locked"}, status_code=423)
            try:
                guard.admit(await request.json())
            except Exception:
                return JSONResponse({"detail": "Evaluation maintenance: request not admitted"}, status_code=423)
        return await call_next(request)


async def main():
    import fcntl
    import uvicorn
    from app.core.config import settings
    from app.core.mesh_gateway import mesh
    from app.services import orchestrator
    from app.main import app

    root = Path("/app/data/evaluation-20261024")
    with (root / "process.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard = OneShotGuard(root)
        if not settings.brave_search_api_key or not settings.mesh_api_key:
            raise RuntimeError("Required credentials unavailable; no paid requests sent")
        real_create = mesh.client.chat.completions.create
        async def create(**kwargs):
            return await guard.mesh_create(real_create, **kwargs)
        mesh._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        real_search = orchestrator.search_web
        async def search(query):
            return await guard.search(real_search, query)
        orchestrator.search_web = search
        settings.max_claims = 2
        settings.max_sources_per_round = 2
        settings.max_search_queries_per_round = 1
        settings.max_contradiction_batches = 1
        settings.mesh_max_output_tokens = 4096
        settings.mesh_json_attempts = 2
        settings.mesh_run_cache = True
        install_admission(app, guard)
        guard.event(event="guard_ready", planned_reservation_usd="0.80",
                    max_new_reservation_usd="1.10", initial_reserved_usd=str(guard.initial_reserved))
        await uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000, workers=1)).serve()


if __name__ == "__main__":
    asyncio.run(main())
