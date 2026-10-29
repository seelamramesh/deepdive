"""Single-process live evaluation using real deployed agents and Mesh only.

Run once on Linux. Reservations intentionally never refunded. This does not
claim invoice-level cost enforcement; it uses conservative published rates.
"""
import asyncio
import argparse
import fcntl
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_budget import EvaluationBudget
from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.services import orchestrator
from app.storage import database


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["sqlite", "uncertainty"], default="sqlite")
    args = parser.parse_args()
    root = Path("/app/data/evaluation-20261024")
    root.mkdir(exist_ok=True)
    with (root / "process.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = root / ("started.json" if args.case == "sqlite" else "started-uncertainty.json")
        if marker.exists():
            raise RuntimeError("Evaluation already started; inspect existing run before any restart")
        if not settings.brave_search_api_key:
            raise RuntimeError("Brave key missing; no paid requests sent")
        budget = EvaluationBudget(root / "budget.json")
        real_create = mesh.client.chat.completions.create
        async def create(**kwargs):
            budget.reserve_mesh(kwargs)
            return await real_create(**kwargs)
        mesh._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        real_search = orchestrator.search_web
        async def search(query):
            budget.reserve_search()
            return await real_search(query)
        orchestrator.search_web = search
        question = "How does SQLite WAL mode differ from rollback journaling for reader/writer concurrency, and what limitations remain?"
        run_id = "eval20261024sql01"
        if args.case == "uncertainty":
            question = "What does the published evidence about K2-18 b establish about extraterrestrial life, and what remains unconfirmed?"
            run_id = "eval20261024exo01"
        marker.write_text(json.dumps({"run_id":run_id,"question":question,
            "max_rounds":1,"configuration":"deployed defaults; one research round",
            "cap_usd":3,"reservation_stop_usd":2.5}),encoding="utf-8")
        await database.init_db()
        print(json.dumps({"started_run_id":run_id}),flush=True)
        run = await orchestrator.run_research(question, max_rounds=1, run_id=run_id)
        summary = {"run_id":run.id,"state":run.current_state.value,"sources":len(run.sources),
            "evidence":len(run.evidence),"claims":len(run.claims),
            "accepted":len(run.supported_claims(run.confidence_threshold)),
            "calls":len(run.agent_calls),"tokens":sum(c.total_tokens or 0 for c in run.agent_calls),
            "missing_usage":sum(c.total_tokens is None for c in run.agent_calls),
            "reserved_usd":str(budget.reserved),"billing_verified":False,
            "warnings":run.warnings,"error":run.error}
        (root / ("result.json" if args.case == "sqlite" else "result-uncertainty.json")).write_text(json.dumps(summary,indent=2),encoding="utf-8")
        print(json.dumps(summary),flush=True)


if __name__ == "__main__":
    asyncio.run(main())
