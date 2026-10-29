import json

import pytest

from app.agents.runner import run_search_strategist
from app.models.schemas import AtomicClaim, ClaimJudgement, ClaimVerdict, ResearchRun, SearchQuery, SubQuestion


@pytest.mark.asyncio
async def test_later_search_uses_rejection_feedback_and_rejects_repeats(monkeypatch):
    run = ResearchRun(question="Market risks in 2026", research_round=2)
    run.claims = [AtomicClaim(id="c1", text="Annual sales doubled", subquestion_id="s1")]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.PARTIALLY_SUPPORTED,
        explanation="Source covers only one quarter",
        missing_evidence="Full-year 2026 sales filing",
    )]
    run.search_queries = [SearchQuery(subquestion_id="s1", query="old broad query")]
    subquestions = [SubQuestion(id="s1", text="Sales trend", completion_criteria="Annual totals")]
    captured = {}

    async def fake_complete(**kwargs):
        captured.update(json.loads(kwargs["user_prompt"]))
        return {"queries": [
            {"subquestion_id": "s1", "query": "OLD BROAD QUERY"},
            {"subquestion_id": "invented", "query": "new query"},
        ]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)

    queries = await run_search_strategist(run, subquestions)

    assert captured["question"] == run.question
    assert run.search_audit[0]["input"]["round"] == 2
    assert run.search_audit[0]["planned_queries"][0]["subquestion_id"] == "s1"
    assert captured["gap_feedback"][0]["failed_claims"][0]["missing_evidence"] == "Full-year 2026 sales filing"
    assert len(queries) == 1
    assert queries[0].subquestion_id == "s1"
    assert "Full-year 2026 sales filing" in queries[0].query
    assert all(query.query.casefold() != "old broad query" for query in queries)
