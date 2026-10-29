"""Labelled synthetic report review plus saved-report replay; shared budget."""
import asyncio
import fcntl
import json
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.evaluation_budget import EvaluationBudget
from app.core.mesh_gateway import mesh
from app.models.schemas import ResearchRun,AtomicClaim,Evidence,ClaimJudgement,ClaimVerdict
from app.services.report_grounding import review_report
from app.storage.database import load_run


async def main():
    root=Path("/app/data/evaluation-20261024")
    with (root/"process.lock").open("w") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        marker=root/"report-review-started.json"
        if marker.exists():
            raise RuntimeError("Already started; inspect saved results")
        budget=EvaluationBudget(root/"budget.json")
        original=mesh.client.chat.completions.create
        async def create(**kwargs):
            budget.reserve_mesh(kwargs)
            return await original(**kwargs)
        mesh._client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        marker.write_text(json.dumps({"synthetic_component_and_saved_replay":True}))
        run=ResearchRun(question="What did fictional Acme report for FY2025?")
        run.evidence=[Evidence(id="e",source_id="s",passage="Acme reported revenue of 10 million USD for FY2025. Profit was 2 million USD.")]
        run.claims=[AtomicClaim(id="c",text="Acme reported revenue of 10 million USD for FY2025.",evidence_ids=["e"])]
        run.judgements=[ClaimJudgement(claim_id="c",verdict=ClaimVerdict.SUPPORTED,confidence=0.95,supporting_evidence_ids=["e"])]
        lines=[run.claims[0].text+" [claim:c] [evidence:e]",
               "Acme's reported FY2025 revenue was USD 10 million. [claim:c] [evidence:e]",
               "Acme reported revenue of 20 million USD for FY2025. [claim:c] [evidence:e]",
               "Acme reported revenue of 10 million USD and profit of 2 million USD for FY2025. [claim:c] [evidence:e]",
               "Acme always earns revenue of 10 million USD every year. [claim:c] [evidence:e]"]
        expected=[True,True,False,False,False]
        run.final_report="\n".join(lines)
        await review_report(run)
        synthetic={"expected_kept":expected,"audit":run.report_grounding_audit,
            "matches_expected":[a["kept"]==e for a,e in zip(run.report_grounding_audit,expected)],
            "calls":[c.model_dump() for c in mesh.drain_calls()]}
        output={"synthetic":synthetic,"reserved_usd":str(budget.reserved),"billing_verified":False}
        target=root/"report-review-results.json"
        target.write_text(json.dumps(output,indent=2))
        print(json.dumps({"synthetic_expected_matches":synthetic["matches_expected"],"reserved_usd":str(budget.reserved)}),flush=True)
        saved=await load_run("eval20261024exo01")
        replay=saved.model_copy(deep=True)
        candidate=json.loads((root/"synthesis-retest-result.json").read_text())
        replay.final_report=candidate["filtered_report"]
        await review_report(replay)
        output["saved_replay"]={"audit":replay.report_grounding_audit,"filtered_report":replay.final_report,
            "calls":[c.model_dump() for c in mesh.drain_calls()],"original_run_not_written":True}
        output["reserved_usd"]=str(budget.reserved)
        target.write_text(json.dumps(output,indent=2))
        print(json.dumps({"replay_reviewed":len(replay.report_grounding_audit),
            "replay_withheld":sum(not a["kept"] for a in replay.report_grounding_audit),
            "reserved_usd":str(budget.reserved)}),flush=True)


if __name__=="__main__":
    asyncio.run(main())
