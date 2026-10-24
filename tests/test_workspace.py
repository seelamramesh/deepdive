from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import routes
from app.models.schemas import AgentCall, ResearchRun, RunState


def api():
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_workspace_uses_real_run_and_hides_raw_agent_output(monkeypatch):
    run = ResearchRun(question="Stored question", current_state=RunState.END)
    run.agent_calls = [AgentCall(agent="judge", response_preview="private raw output", error="raw failure")]
    run.warnings = ["Later research stage failed; report uses last verified checkpoint: raw malformed JSON"]

    async def load(_run_id):
        return run

    monkeypatch.setattr(routes, "load_run", load)
    result = api().get(f"/runs/{run.id}/workspace")
    assert result.status_code == 200
    assert result.json()["question"] == "Stored question"
    assert result.json()["accepted_claim_ids"] == []
    assert "response_preview" not in result.json()["agent_calls"][0]
    assert "error" not in result.json()["agent_calls"][0]
    assert "raw malformed JSON" not in result.text
    assert "Partial recovery" in result.json()["warnings"][0]


def test_run_list_and_missing_workspace(monkeypatch):
    async def listing():
        return [{"id": "existing", "question": "Real question", "state": "END", "created_at": "2026-10-24"}]

    async def missing(_run_id):
        return None

    monkeypatch.setattr(routes, "list_runs", listing)
    monkeypatch.setattr(routes, "load_run", missing)
    assert api().get("/runs").json()[0]["id"] == "existing"
    assert api().get("/runs/missing/workspace").status_code == 404


def test_health_reports_degraded_when_database_unavailable(monkeypatch):
    async def unavailable():
        return False

    monkeypatch.setattr(routes, "database_ready", unavailable)
    result = api().get("/health")
    assert result.json()["status"] == "degraded"
    assert result.json()["db_ok"] is False


def test_workspace_derives_counts_without_rewriting_recorded_assessment(monkeypatch):
    from app.models.schemas import AtomicClaim, ClaimJudgement, ClaimVerdict, CoverageEntry, Evidence, Source, SubQuestion
    run = ResearchRun(question='Historical coverage fixture',
        subquestions=[SubQuestion(id='sq',text='Area')],
        sources=[Source(id='s',url='https://fixture.example')],
        evidence=[Evidence(id='e',source_id='s',subquestion_id='sq',passage='Fact')],
        claims=[AtomicClaim(id='c',text='Fact',subquestion_id='sq',evidence_ids=['e'])],
        judgements=[ClaimJudgement(claim_id='c',verdict=ClaimVerdict.SUPPORTED,confidence=0.9,supporting_evidence_ids=['e'])],
        coverage=[CoverageEntry(subquestion_id='sq',verified_claim_count=0)])
    async def load(_):return run
    monkeypatch.setattr(routes,'load_run',load)
    data=api().get(f'/runs/{run.id}/workspace').json()
    assert data['coverage'][0]['verified_claim_count']==1
    assert data['recorded_coverage'][0]['verified_claim_count']==0
    assert run.coverage[0].verified_claim_count==0


def test_workspace_exposes_review_status_and_final_inclusion_without_backfill(monkeypatch):
    run=ResearchRun(question="Reviewed fixture",report_grounding_status="accepted_claim_fallback",
        report_fallback_reason="All prose withheld",report_grounding_audit=[{
            "unit_id":"0","text":"Unapproved detail","kept":False,
            "included_in_final_report":False,"reason":"Unsupported"}])
    async def load(_): return run
    monkeypatch.setattr(routes,"load_run",load)
    data=api().get(f"/runs/{run.id}/workspace").json()
    assert data["report_grounding_status"]=="accepted_claim_fallback"
    assert data["report_grounding_audit"][0]["reason"]=="Unsupported"
    run.report_grounding_audit=[]
    run.report_grounding_status="not_available"
    historical=api().get(f"/runs/{run.id}/workspace").json()
    assert historical["report_grounding_audit"]==[]
    assert historical["report_grounding_status"]=="not_available"


def test_workspace_discloses_shared_material_without_rewriting_sources(monkeypatch):
    from app.models.schemas import Source
    run=ResearchRun(question='Source provenance',sources=[
        Source(id='a',url='https://a.example',work_identifiers=['doi:10.1234/shared']),
        Source(id='b',url='https://b.example',work_identifiers=['doi:10.1234/shared'])])
    async def load(_): return run
    monkeypatch.setattr(routes,'load_run',load)
    data=api().get(f'/runs/{run.id}/workspace').json()
    assert data['source_material_groups']['a']==data['source_material_groups']['b']
    assert 'do not prove independence' in data['source_independence_note']
    assert len(data['sources'])==2
    assert all(s['publication_date'] is None for s in data['sources'])
