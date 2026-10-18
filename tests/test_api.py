from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.models.schemas import (
    AtomicClaim,
    ClaimJudgement,
    ClaimVerdict,
    Evidence,
    ResearchRun,
)


def client() -> TestClient:
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def threshold_run() -> ResearchRun:
    run = ResearchRun(question="A sufficiently detailed research question")
    run.evidence = [Evidence(id="e1", source_id="s1", passage="Exact evidence")]
    run.claims = [
        AtomicClaim(id="high", text="High confidence", evidence_ids=["e1"]),
        AtomicClaim(id="low", text="Low confidence", evidence_ids=["e1"]),
    ]
    run.judgements = [
        ClaimJudgement(
            claim_id="high",
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.9,
            supporting_evidence_ids=["e1"],
        ),
        ClaimJudgement(
            claim_id="low",
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.6,
            supporting_evidence_ids=["e1"],
        ),
    ]
    return run


def test_research_request_validation_rejects_short_question():
    response = client().post("/research", json={"question": "short"})

    assert response.status_code == 422


def test_missing_run_endpoints_return_404(monkeypatch):
    async def missing(_run_id):
        return None

    monkeypatch.setattr(routes, "load_run", missing)
    api = client()

    for path in (
        "/runs/missing",
        "/runs/missing/audit",
        "/runs/missing/claims",
        "/runs/missing/contradictions",
        "/runs/missing/certificate",
        "/runs/missing/report",
        "/runs/missing/evaluation",
    ):
        assert api.get(path).status_code == 404


def test_summary_and_claims_use_configured_confidence_threshold(monkeypatch):
    run = threshold_run()

    async def load(_run_id):
        return run

    monkeypatch.setattr(routes, "load_run", load)
    monkeypatch.setattr(routes.settings, "confidence_threshold", 0.7)
    api = client()

    summary = api.get(f"/runs/{run.id}")
    claims = api.get(f"/runs/{run.id}/claims")

    assert summary.status_code == 200
    assert summary.json()["supported_claim_count"] == 1
    assert [item["id"] for item in claims.json()["supported"]] == ["high"]
    assert [item["id"] for item in claims.json()["rejected"]] == ["low"]


def test_certificate_is_unavailable_before_completion(monkeypatch):
    run = threshold_run()

    async def load(_run_id):
        return run

    monkeypatch.setattr(routes, "load_run", load)

    response = client().get(f"/runs/{run.id}/certificate")

    assert response.status_code == 400
    assert "no certificate" in response.json()["detail"]
