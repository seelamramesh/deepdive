import json
import pytest
from app.models.schemas import ResearchRun,AtomicClaim,Evidence,ClaimJudgement,ClaimVerdict
from app.services.report_grounding import review_report


def report():
    run=ResearchRun(question="Fixture revenue")
    run.evidence=[Evidence(id="e",source_id="s",passage="Revenue was 10 million. Profit was 2 million.")]
    run.claims=[AtomicClaim(id="c",text="Revenue was 10 million.",evidence_ids=["e"])]
    run.judgements=[ClaimJudgement(claim_id="c",verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,supporting_evidence_ids=["e"])]
    run.final_report="# Findings\nRevenue was 10 million. [claim:c] [evidence:e]\nRevenue was 10 million and profit was 2 million. [claim:c] [evidence:e]"
    return run


@pytest.mark.asyncio
async def test_review_supplies_claims_and_passages_and_withholds_extra_clause(monkeypatch):
    run=report()
    async def complete(**kwargs):
        payload=json.loads(kwargs["user_prompt"])
        assert payload["accepted_claims"][0]["text"]=="Revenue was 10 million."
        assert "Profit" in payload["evidence"][0]["passage"]
        return {"decisions":[{"unit_id":u["unit_id"],"supported":"profit" not in u["text"],
            "reason":"Extra profit fact not an accepted claim"} for u in payload["units"]]}
    monkeypatch.setattr("app.services.report_grounding.mesh.complete",complete)
    await review_report(run)
    assert "profit" not in run.final_report
    assert "Revenue was 10 million." in run.final_report
    assert len(run.report_grounding_audit)==3
    assert run.report_grounding_audit[-1]["kept"] is False


@pytest.mark.asyncio
async def test_missing_duplicate_and_string_approval_withhold_units(monkeypatch):
    run=report()
    async def complete(**kwargs):
        return {"decisions":[{"unit_id":"0","supported":True},
            {"unit_id":"0","supported":True},{"unit_id":"1","supported":"true"},
            {"unit_id":"invented","supported":True}]}
    monkeypatch.setattr("app.services.report_grounding.mesh.complete",complete)
    await review_report(run)
    assert not run.final_report.strip()
    assert not any(item["kept"] for item in run.report_grounding_audit)


@pytest.mark.asyncio
async def test_reviewer_failure_leaves_audit_and_warning_without_prose(monkeypatch):
    run=report()
    async def complete(**kwargs):
        raise RuntimeError("Fixture failure")
    monkeypatch.setattr("app.services.report_grounding.mesh.complete",complete)
    await review_report(run)
    assert not run.final_report.strip()
    assert len(run.report_grounding_audit)==3
    assert run.warnings
