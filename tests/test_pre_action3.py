import json
from pathlib import Path
import httpx
import pytest
from app.services import retrieval

FIXTURE = Path(__file__).parent / "fixtures/action2-ee166f04883a48c0.json"

@pytest.fixture
def action2():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))

@pytest.mark.asyncio
@pytest.mark.parametrize("case,expected,http_status", [
    ("empty", "empty", 200), ("bad_json", "invalid_response", 200),
    ("http_error", "error", 429), ("timeout", "timeout", None),
    ("success", "success", 200), ("missing_key", "missing_key", None),
])
async def test_search_outcomes_are_safe_and_distinct(monkeypatch, case, expected, http_status):
    original = httpx.AsyncClient
    def respond(request):
        if case == "timeout": raise httpx.ReadTimeout("secret must not appear")
        if case == "bad_json": return httpx.Response(200, text="secret invalid JSON")
        if case == "http_error": return httpx.Response(429, text="private response")
        return httpx.Response(200, json={"web":{"results":[{"url":"https://fda.gov/source"}] if case=="success" else []}})
    monkeypatch.setattr(retrieval.settings,"brave_search_api_key", "" if case=="missing_key" else "secret")
    monkeypatch.setattr(retrieval.httpx,"AsyncClient",lambda **kw: original(transport=httpx.MockTransport(respond),**kw))
    monkeypatch.setattr(retrieval,"validate_url",lambda url:(True,""))
    retrieval.drain_search_events()
    await retrieval.search_web("test query")
    event, = retrieval.drain_search_events()
    assert event["status"] == expected and event["http_status"] == http_status
    assert event["attempt_id"] and event["duration_ms"] >= 0 and event["timestamp"]
    assert "secret" not in json.dumps(event) and "private response" not in json.dumps(event)
    assert event["request_sent"] is (case!="missing_key")

@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403,404])
async def test_fetch_http_status_is_retained_without_body(monkeypatch,status):
    original=httpx.AsyncClient
    monkeypatch.setattr(retrieval,"validate_url",lambda url:(True,""))
    monkeypatch.setattr(retrieval.httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(status,text="private body")),**kw))
    retrieval.drain_fetch_events()
    assert await retrieval.fetch_url("https://www.fsis.usda.gov/fixture") is None
    event,=retrieval.drain_fetch_events()
    assert event["http_status"]==status and event["error_class"]=="HTTPStatusError"
    assert event["attempt_id"] and "private body" not in json.dumps(event)


@pytest.mark.asyncio
async def test_action2_backfill_carries_urls_and_does_not_retry_failure(monkeypatch,action2):
    from app.models.schemas import ResearchRun, Source, SearchQuery
    from app.services import orchestrator as o
    run=ResearchRun(question=action2["question"],research_round=1)
    first=action2["retrieval_audit"][0]
    seeds=first["seed_urls"]
    alternatives=first["searches"][0]["result_urls"]
    query=SearchQuery(id="q",query="official query",subquestion_id="sq")
    async def search(query):return alternatives
    seen=[]
    async def fetch(urls):
        url,=urls;seen.append(url)
        if url==seeds[1]:return []
        return [Source(id=str(len(seen)),url=url,content_hash=str(len(seen)))]
    monkeypatch.setattr(o,"search_web",search);monkeypatch.setattr(o,"fetch_sources",fetch)
    monkeypatch.setattr(o.settings,"max_sources_per_round",2)
    monkeypatch.setattr(o.settings,"max_fetch_attempts_per_round",4)
    await o._retrieve_with_backfill(run,seeds,[query])
    assert seen==seeds+[alternatives[0]] and len(run.sources)==2
    assert run.retrieval_pending[0]["url"]==alternatives[1]
    assert run.retrieval_pending[0]["provenance"][0]["subquestion_id"]=="sq"
    run.research_round=2
    await o._retrieve_with_backfill(run,seeds,[])
    assert seen==seeds+alternatives and seen.count(seeds[1])==1
    assert not run.retrieval_pending


@pytest.mark.asyncio
async def test_fetch_attempt_limit_is_separate_from_success_slots(monkeypatch):
    from app.models.schemas import ResearchRun
    from app.services import orchestrator as o
    run=ResearchRun(question="Bound all failed fetches")
    seen=[]
    async def fail(urls):seen.extend(urls);return []
    monkeypatch.setattr(o,"fetch_sources",fail)
    monkeypatch.setattr(o.settings,"max_sources_per_round",2)
    monkeypatch.setattr(o.settings,"max_fetch_attempts_per_round",3)
    await o._retrieve_with_backfill(run,[f"https://example.org/{i}" for i in range(20)],[])
    assert len(seen)==3 and len(run.retrieval_pending)==17 and not run.sources


def test_action2_deterministic_limitations_preserve_strict_facts_and_are_idempotent(action2):
    import hashlib
    from app.models.schemas import ResearchRun
    from app.services.orchestrator import _verify_report_citations
    before=hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    run=ResearchRun.model_validate(action2)
    run.final_report += "\nInvented limitation: all food products are automatically approved."
    _verify_report_citations(run)
    assert "automatically approved" not in run.final_report
    assert "## Run limitations (recorded artifacts)" in run.final_report
    assert "0 passages; 0 accepted claims; 0 sources" in run.final_report
    assert "does not establish agreement" in run.final_report
    assert len(run.report_grounding_audit)==19 and len(run.report_artifact_audit)==9
    assert all(item["method"]=="deterministic_artifact" for item in run.report_artifact_audit)
    first=run.final_report
    _verify_report_citations(run)
    assert run.final_report==first
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest()==before


@pytest.mark.asyncio
async def test_action2_judge_qualifiers_reach_drafter_without_becoming_evidence(monkeypatch,action2):
    from app.models.schemas import ResearchRun
    from app.agents.runner import run_claim_drafter, _revision_feedback
    run=ResearchRun.model_validate(action2)
    captured=[]
    async def complete(**kwargs):captured.append(kwargs);return {"claims":[]}
    monkeypatch.setattr("app.agents.runner.mesh.complete",complete)
    await run_claim_drafter(run,run.evidence,run.subquestions)
    prompt=json.loads(captured[0]["user_prompt"])
    feedback=prompt["revision_feedback"]
    assert any("FMIA" in f.get("missing_evidence","") and f["source"]=="judge" for f in feedback)
    assert any(f["claim_id"]=="79e238c4b05c" for f in feedback)
    assert prompt["feedback_is_evidence"] is False
    assert len(prompt["evidence"])==9
    assert "NOT evidence" in captured[0]["system_prompt"]
    run.search_audit*=100
    result=_revision_feedback(run,run.subquestions)
    assert len(result)<=12 and all(len(item.get("missing_evidence",""))<=800 for item in result)
    # Prompt transport is checked here; no mocked verdict claims live semantic success.


@pytest.mark.asyncio
async def test_workspace_exposes_transport_details_and_unknown_history(monkeypatch,tmp_path,action2):
    from app.storage import database
    from app.main import app
    from app.models.schemas import ResearchRun
    monkeypatch.setattr(database,"DB_PATH",str(tmp_path/"fixture.db"))
    await database.init_db()
    run=ResearchRun.model_validate(action2)
    run.retrieval_audit.append({"round":3,"searches":[{"status":"error","http_status":429,"error_class":"HTTPStatusError","attempt_id":"offline","duration_ms":1}]})
    await database.save_run(run)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
        data=(await client.get(f"/runs/{run.id}/workspace")).json()
    assert data["retrieval_audit"][-1]["searches"][0]["http_status"]==429
    assert data["agent_calls"][0]["cache_miss_reason"] is None
    assert data["agent_calls"][0]["cache_store_status"] is None


@pytest.mark.asyncio
async def test_redirect_http_hops_share_attempt_id_but_keep_status(monkeypatch):
    original=httpx.AsyncClient
    def respond(request):
        if request.url.path=="/old":return httpx.Response(302,headers={"location":"/new"})
        return httpx.Response(200,headers={"content-type":"text/plain"},text="Official source text")
    monkeypatch.setattr(retrieval,"validate_url",lambda url:(True,""))
    monkeypatch.setattr(retrieval.httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    retrieval.drain_fetch_events()
    assert await retrieval.fetch_url("https://fda.gov/old")
    events=retrieval.drain_fetch_events()
    assert [e["http_status"] for e in events]==[302,200]
    assert [e["request_index"] for e in events]==[1,2]
    assert len({e["attempt_id"] for e in events})==1


@pytest.mark.asyncio
async def test_known_subquestion_backfill_prefers_matching_alternative(monkeypatch):
    from app.models.schemas import ResearchRun, Source
    from app.services import orchestrator as o
    run=ResearchRun(question="Owner-aware bounded queue",retrieval_pending=[
        {"url":"https://example.org/fail", "provenance":[{"origin":"search","subquestion_id":"a"}]},
        {"url":"https://example.org/b", "provenance":[{"origin":"search","subquestion_id":"b"}]},
        {"url":"https://example.org/a", "provenance":[{"origin":"search","subquestion_id":"a"}]}])
    seen=[]
    async def fetch(urls):
        url,=urls;seen.append(url)
        return [] if url.endswith('/fail') else [Source(url=url)]
    monkeypatch.setattr(o,"fetch_sources",fetch)
    monkeypatch.setattr(o.settings,"max_sources_per_round",1)
    await o._retrieve_with_backfill(run,[],[])
    assert seen==['https://example.org/fail','https://example.org/a']
