"""Action 3 contract checks with fake I/O, never live quality measurements."""
import json
import httpx
import pytest
from app.models.schemas import (ResearchRun, Source, Evidence, AtomicClaim, SubQuestion,
    SearchQuery, ClaimJudgement, ClaimVerdict, CoverageEntry, CoverageStatus, _hash)
from app.services import orchestrator as o
from app.storage import database


@pytest.mark.asyncio
@pytest.mark.parametrize("case",["false_premise","drafter_timeout","all_fetches_fail","late_failure","error_pages"])
async def test_action3_offline_pipeline_contract(monkeypatch,tmp_path,case):
    monkeypatch.setattr(database,"DB_PATH",str(tmp_path/"offline.db"))
    await database.init_db()
    question=("What caused the 2025 Mars crewed landing failure?" if case=="false_premise" else "Offline failure contract: what does the supplied source establish?")
    text=("Offline source supplies no evidence of the alleged event." if case=="false_premise" else "Observed measurement was 10 units.")
    source=Source(id="s",url="https://fixture.example/primary",content_hash=_hash(text),content_snapshot=text)
    evidence=Evidence(id="e",source_id="s",subquestion_id="sq",passage=text,source_snapshot_hash=_hash(text))
    claim=AtomicClaim(id="c",text=text,evidence_ids=["e"],subquestion_id="sq")
    async def planner(run):return [SubQuestion(id="sq",text="Verify supplied premise and evidence")]
    async def strategy(*args):return [SearchQuery(id="q",query="fixture primary",subquestion_id="sq")]
    async def search(query):return [source.url]
    async def fetch(urls):return [] if case=="all_fetches_fail" else [source]
    async def researcher(*args):return [evidence]
    async def critic(*args):return {"s":{"trust_score":.9,"factors":{"primary_source":True}}}
    async def draft(*args):
        if case=="false_premise":raise AssertionError("Fabricated passage must not reach drafter")
        if case=="drafter_timeout":raise TimeoutError("Simulated Mesh drafter timeout")
        return [claim]
    async def prosecution(*args):return []
    async def defense(*args):return []
    async def judge(*args):return [ClaimJudgement(claim_id="c",verdict=ClaimVerdict.SUPPORTED,confidence=.9,supporting_evidence_ids=["e"])]
    async def contradictions(*args):
        if case=="late_failure":raise TimeoutError("Simulated failure after accepted checkpoint")
        return []
    async def coverage(*args):return [CoverageEntry(subquestion_id="sq",status=CoverageStatus.GREEN)]
    async def synthesis(*args):return "# Offline fixture\nObserved measurement was 10 units. [claim:c] [evidence:e]"
    async def complete(**kwargs):
        if kwargs["agent_name"]=="researcher":
            return {"evidence":[{"source_id":"s","subquestion_id":"sq","passage":"Crewed Mars landing failed in 2025 because an engine exploded."}]}
        if kwargs["agent_name"]=="report_verifier":
            payload=json.loads(kwargs["user_prompt"])
            return {"decisions":[{"unit_id":unit["unit_id"],"supported":True,"reason":"Mocked contract decision"} for unit in payload["units"]]}
        raise AssertionError("Unexpected unmocked agent")
    for name,fn in [("run_planner",planner),("run_search_strategist",strategy),("search_web",search),
        ("fetch_sources",fetch),("run_researcher",researcher),("run_source_critic",critic),("run_claim_drafter",draft),
        ("run_prosecutor",prosecution),("run_defense",defense),("run_judge",judge),
        ("run_contradiction_analyst",contradictions),("run_coverage_analyst",coverage),("run_synthesizer",synthesis)]:
        monkeypatch.setattr(o,name,fn)
    monkeypatch.setattr("app.core.mesh_gateway.mesh.complete",complete)
    if case=="false_premise":
        from app.agents.runner import run_researcher
        monkeypatch.setattr(o,"run_researcher",run_researcher)
    if case=="error_pages":
        from app.services import retrieval
        original=httpx.AsyncClient
        monkeypatch.setattr(retrieval,"validate_url",lambda url:(True,""))
        monkeypatch.setattr(retrieval.httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(404,text="Error page, not research evidence")),**kw))
        monkeypatch.setattr(o,"fetch_sources",retrieval.fetch_sources)
    result=await o.run_research(question,max_rounds=1)
    saved=await database.load_run(result.id)
    assert saved is not None and saved.current_state==result.current_state
    if case=="drafter_timeout":
        assert result.current_state.value=="FAILED" and result.error
        assert len(saved.sources)==len(saved.evidence)==1 and not saved.supported_claims(.7)
        assert saved.certificate is None
    elif case=="late_failure":
        assert result.current_state.value=="END" and result.warnings
        assert saved.supported_claims(.7) and "Observed measurement" in saved.final_report
        assert any("checkpoint" in warning for warning in saved.warnings)
    else:
        assert result.current_state.value=="END" and not result.supported_claims(.7)
        assert "Insufficient verified evidence" in result.final_report
        assert "engine exploded" not in result.final_report
    if case=="false_premise":
        assert not saved.evidence and not saved.claims
    if case=="error_pages":
        event=saved.retrieval_audit[0]["fetch_outcomes"][0]
        assert event["http_status"]==404 and event["error_class"]=="HTTPStatusError"
        assert not saved.sources
