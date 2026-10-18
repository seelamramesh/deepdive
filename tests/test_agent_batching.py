import json

import pytest

from app.agents.runner import (
    run_contradiction_analyst,
    run_defense,
    run_judge,
    run_prosecutor,
    run_researcher,
    run_search_strategist,
    run_source_critic,
)
from app.models.schemas import AtomicClaim, DefenseArgument, Evidence, ProsecutorArgument, ResearchRun, SubQuestion


@pytest.mark.asyncio
async def test_source_critic_batches_and_rejects_unknown_source_ids(monkeypatch):
    calls = []
    sources = [{"source_id": f"s{index}"} for index in range(7)]

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        return {"scores": [
            {"source_id": source["source_id"], "trust_score": 0.8, "factors": {}}
            for source in payload["sources"]
        ] + [{"source_id": "invented", "trust_score": 1.0}]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    scores = await run_source_critic(ResearchRun(question="question"), sources)

    assert [len(call["sources"]) for call in calls] == [3, 3, 1]
    assert set(scores) == {f"s{index}" for index in range(7)}


@pytest.mark.asyncio
async def test_search_strategist_fills_missing_subquestions(monkeypatch):
    subquestions = [
        SubQuestion(id="s1", text="First topic"),
        SubQuestion(id="s2", text="Second topic"),
    ]

    async def fake_complete(**kwargs):
        return {"queries": [{"subquestion_id": "s1", "query": "first query"}]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    queries = await run_search_strategist(ResearchRun(question="question"), subquestions)

    assert {query.subquestion_id for query in queries} == {"s1", "s2"}
    assert any(query.query == "Second topic authoritative source" for query in queries)


def make_claims(count=7):
    return [
        AtomicClaim(id=f"c{index}", text=f"Claim {index}", evidence_ids=[f"e{index}"])
        for index in range(count)
    ]


def make_evidence(count=7):
    return [
        Evidence(id=f"e{index}", source_id=f"s{index}", passage=f"Passage {index}")
        for index in range(count)
    ]


@pytest.mark.asyncio
async def test_prosecutor_batches_claims_and_scopes_evidence(monkeypatch):
    calls = []

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        return {"arguments": [{"claim_id": claim["id"]} for claim in payload["claims"]]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    result = await run_prosecutor(ResearchRun(question="question"), make_claims(), make_evidence())

    assert [len(call["claims"]) for call in calls] == [3, 3, 1]
    assert all(len(call["evidence"]) == len(call["claims"]) for call in calls)
    assert len(result) == 7


@pytest.mark.asyncio
async def test_defense_batches_claims(monkeypatch):
    calls = []

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        return {"defenses": [{"claim_id": claim["id"]} for claim in payload["claims"]]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    result = await run_defense(ResearchRun(question="question"), make_claims(), make_evidence())

    assert [len(call["claims"]) for call in calls] == [3, 3, 1]
    assert len(result) == 7


@pytest.mark.asyncio
async def test_judge_batches_matching_arguments(monkeypatch):
    claims = make_claims()
    prosecution = [ProsecutorArgument(claim_id=claim.id) for claim in claims]
    defense = [DefenseArgument(claim_id=claim.id) for claim in claims]
    calls = []

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        return {"verdicts": [
            {"claim_id": claim["id"], "verdict": "unsupported", "confidence": 0.4}
            for claim in payload["claims"]
        ]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    result = await run_judge(ResearchRun(question="question"), claims, prosecution, defense, 0.7)

    assert [len(call["claims"]) for call in calls] == [3, 3, 1]
    assert all(len(call["prosecution"]) == len(call["claims"]) for call in calls)
    assert len(result) == 7


@pytest.mark.asyncio
async def test_judge_rejects_invented_evidence_and_fills_omitted_claim(monkeypatch):
    claims = make_claims(2)

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        return {"verdicts": [{
            "claim_id": payload["claims"][0]["id"],
            "verdict": "supported",
            "confidence": 0.99,
            "supporting_evidence_ids": ["invented"],
        }]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    result = await run_judge(ResearchRun(question="question"), claims, [], [], 0.7)

    assert len(result) == 2
    assert all(item.verdict.value == "unsupported" for item in result)
    assert {item.claim_id for item in result} == {"c0", "c1"}


@pytest.mark.asyncio
async def test_researcher_uses_one_source_per_call_and_caps_evidence(monkeypatch):
    calls = []
    sources = [
        {"source_id": f"s{index}", "url": f"https://example.com/{index}",
         "title": f"Source {index}", "content": "Exact passage"}
        for index in range(2)
    ]

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        source_id = payload["sources"][0]["source_id"]
        return {"evidence": [
            {"source_id": source_id, "passage": "Exact passage", "relevance": 0.9}
            for _ in range(8)
        ]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    result = await run_researcher(ResearchRun(question="question"), sources, [])

    assert len(calls) == 2
    assert all(len(call["sources"]) == 1 for call in calls)
    assert len(result) == 12


@pytest.mark.asyncio
async def test_contradiction_analyst_batches_by_subquestion_and_scopes_evidence(monkeypatch):
    claims = make_claims(8)
    for index, claim in enumerate(claims):
        claim.subquestion_id = "sq1" if index < 7 else "sq2"
    evidence = make_evidence(8)
    calls = []

    async def fake_complete(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        calls.append(payload)
        if len(payload["claims"]) < 2:
            return {"contradictions": []}
        return {"contradictions": [{
            "topic": "Conflict",
            "claim_a": payload["claims"][0]["text"],
            "claim_b": payload["claims"][1]["text"],
            "evidence_a": [payload["evidence"][0]["id"]],
            "evidence_b": [payload["evidence"][1]["id"]],
        }]}

    monkeypatch.setattr("app.agents.runner.mesh.complete", fake_complete)
    result = await run_contradiction_analyst(ResearchRun(question="question"), claims, evidence)

    assert [len(call["claims"]) for call in calls] == [6, 1, 1]
    assert all(len(call["claims"]) <= 6 for call in calls)
    assert len(result) == 1
