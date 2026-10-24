"""Synthetic component test with real Mesh, shared conservative budget."""
import asyncio
import fcntl
import json
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_budget import EvaluationBudget
from app.core.mesh_gateway import mesh
from app.agents.runner import run_contradiction_analyst
from app.models.schemas import AtomicClaim, Evidence, ResearchRun


async def main():
    root = Path("/app/data/evaluation-20261024")
    with (root / "process.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = root / "contradiction-fixtures-started.json"
        if marker.exists():
            raise RuntimeError("Already started; inspect existing results")
        budget = EvaluationBudget(root / "budget.json")
        original = mesh.client.chat.completions.create
        async def create(**kwargs):
            budget.reserve_mesh(kwargs)
            return await original(**kwargs)
        mesh._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        fixture_path = Path(__file__).resolve().parents[1] / "evaluations/contradiction-labelled-fixtures.json"
        fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
        marker.write_text(json.dumps({"synthetic":True,"cases":[c["id"] for c in fixtures["cases"]]}),encoding="utf-8")
        results = []
        for case in fixtures["cases"]:
            evidence = [Evidence(id=f"e{i}",source_id=f"s{i}",passage=text) for i,text in enumerate(case["passages"])]
            claims = [AtomicClaim(id=f"c{i}",text=e.passage,evidence_ids=[e.id]) for i,e in enumerate(evidence)]
            run = ResearchRun(question="Compare fictional Acme revenue for matching reporting periods.")
            detected = await run_contradiction_analyst(run,claims,evidence)
            calls = mesh.drain_calls()
            results.append({"case":case,"detected":[c.model_dump() for c in detected],
                "matches_expected":bool(detected)==case["expected_contradiction"],
                "audit":run.contradiction_audit,"calls":[c.model_dump() for c in calls]})
            (root / "contradiction-fixture-results.json").write_text(json.dumps({
                "synthetic":True,"results":results,"reserved_usd":str(budget.reserved),
                "billing_verified":False},indent=2),encoding="utf-8")
            print(json.dumps({"case":case["id"],"matches_expected":results[-1]["matches_expected"],
                "retained":len(detected),"reserved_usd":str(budget.reserved)}),flush=True)


if __name__ == "__main__":
    asyncio.run(main())
