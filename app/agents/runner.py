"""Agent runner — calls each agent through MeshGateway with typed I/O."""

from __future__ import annotations

import json
from typing import Any

from app.agents import prompts
from app.core.mesh_gateway import mesh
from app.models.schemas import (
    AtomicClaim,
    ClaimJudgement,
    ClaimVerdict,
    Contradiction,
    ContradictionResolution,
    ContradictionSeverity,
    ContradictionType,
    CoverageEntry,
    CoverageStatus,
    DefenseArgument,
    Evidence,
    ProsecutorArgument,
    ResearchRun,
    SearchQuery,
    SubQuestion,
)


async def run_planner(run: ResearchRun) -> list[SubQuestion]:
    """Break question into subquestions."""
    result = await mesh.complete(
        agent_name="planner",
        system_prompt=prompts.PLANNER_PROMPT,
        user_prompt=f"Research question: {run.question}",
        response_format={"type": "json_object"},
    )
    subs = []
    for item in result.get("subquestions", []):
        sq = SubQuestion(
            text=item["text"],
            completion_criteria=item.get("completion_criteria", ""),
            parent_question=run.question,
        )
        subs.append(sq)
    return subs


async def run_search_strategist(
    run: ResearchRun, subquestions: list[SubQuestion]
) -> list[SearchQuery]:
    """Generate search queries for subquestions."""
    sq_data = [{"id": s.id, "text": s.text} for s in subquestions]
    result = await mesh.complete(
        agent_name="search_strategist",
        system_prompt=prompts.SEARCH_STRATEGIST_PROMPT,
        user_prompt=json.dumps({"subquestions": sq_data}),
        response_format={"type": "json_object"},
    )
    queries = []
    for item in result.get("queries", []):
        q = SearchQuery(
            subquestion_id=item.get("subquestion_id", ""),
            query=item["query"],
            source_preference=item.get("source_preference", ""),
        )
        queries.append(q)
    return queries


async def run_researcher(
    run: ResearchRun,
    source_contents: list[dict[str, str]],
    subquestions: list[SubQuestion],
) -> list[Evidence]:
    """Extract evidence from source content."""
    sq_data = [{"id": s.id, "text": s.text} for s in subquestions]
    result = await mesh.complete(
        agent_name="researcher",
        system_prompt=prompts.RESEARCHER_PROMPT,
        user_prompt=json.dumps({
            "subquestions": sq_data,
            "sources": source_contents,
        }),
        response_format={"type": "json_object"},
    )
    evidence_list = []
    for item in result.get("evidence", []):
        e = Evidence(
            source_id=item["source_id"],
            subquestion_id=item.get("subquestion_id", ""),
            passage=item["passage"],
            relevance=item.get("relevance", 0.5),
        )
        e.compute_hash()
        evidence_list.append(e)
    return evidence_list


async def run_source_critic(
    run: ResearchRun, sources: list[dict],
) -> dict[str, dict]:
    """Score source trustworthiness."""
    result = await mesh.complete(
        agent_name="source_critic",
        system_prompt=prompts.SOURCE_CRITIC_PROMPT,
        user_prompt=json.dumps({"sources": sources}),
        response_format={"type": "json_object"},
    )
    scores = {}
    for item in result.get("scores", []):
        scores[item["source_id"]] = {
            "trust_score": item.get("trust_score", 0.5),
            "factors": item.get("factors", {}),
            "limitations": item.get("limitations", ""),
        }
    return scores


async def run_claim_drafter(
    run: ResearchRun,
    evidence: list[Evidence],
    subquestions: list[SubQuestion],
) -> list[AtomicClaim]:
    """Draft atomic claims from evidence."""
    ev_data = [
        {"id": e.id, "source_id": e.source_id, "subquestion_id": e.subquestion_id,
         "passage": e.passage}
        for e in evidence
    ]
    sq_data = [{"id": s.id, "text": s.text} for s in subquestions]
    result = await mesh.complete(
        agent_name="claim_drafter",
        system_prompt=prompts.CLAIM_DRAFTER_PROMPT,
        user_prompt=json.dumps({"evidence": ev_data, "subquestions": sq_data}),
        response_format={"type": "json_object"},
    )
    claims = []
    for item in result.get("claims", []):
        c = AtomicClaim(
            text=item["text"],
            evidence_ids=item.get("evidence_ids", []),
            subquestion_id=item.get("subquestion_id", ""),
        )
        claims.append(c)
    return claims


async def run_prosecutor(
    run: ResearchRun,
    claims: list[AtomicClaim],
    evidence: list[Evidence],
) -> list[ProsecutorArgument]:
    """Argue against each claim."""
    claims_data = [
        {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids}
        for c in claims
    ]
    ev_data = [
        {"id": e.id, "passage": e.passage, "source_id": e.source_id}
        for e in evidence
    ]
    result = await mesh.complete(
        agent_name="prosecutor",
        system_prompt=prompts.PROSECUTOR_PROMPT,
        user_prompt=json.dumps({"claims": claims_data, "evidence": ev_data}),
        response_format={"type": "json_object"},
    )
    args = []
    for item in result.get("arguments", []):
        args.append(ProsecutorArgument(
            claim_id=item["claim_id"],
            weaknesses=item.get("weaknesses", []),
            unsupported_components=item.get("unsupported_components", []),
        ))
    return args


async def run_defense(
    run: ResearchRun,
    claims: list[AtomicClaim],
    evidence: list[Evidence],
) -> list[DefenseArgument]:
    """Map claims to supporting passages."""
    claims_data = [
        {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids}
        for c in claims
    ]
    ev_data = [
        {"id": e.id, "passage": e.passage, "source_id": e.source_id}
        for e in evidence
    ]
    result = await mesh.complete(
        agent_name="defense",
        system_prompt=prompts.DEFENSE_PROMPT,
        user_prompt=json.dumps({"claims": claims_data, "evidence": ev_data}),
        response_format={"type": "json_object"},
    )
    defs = []
    for item in result.get("defenses", []):
        defs.append(DefenseArgument(
            claim_id=item["claim_id"],
            supporting_passages=item.get("supporting_passages", []),
        ))
    return defs


async def run_judge(
    run: ResearchRun,
    claims: list[AtomicClaim],
    prosecution: list[ProsecutorArgument],
    defense: list[DefenseArgument],
    confidence_threshold: float,
) -> list[ClaimJudgement]:
    """Render verdicts on claims."""
    result = await mesh.complete(
        agent_name="judge",
        system_prompt=prompts.JUDGE_PROMPT,
        user_prompt=json.dumps({
            "claims": [{"id": c.id, "text": c.text} for c in claims],
            "prosecution": [a.model_dump() for a in prosecution],
            "defense": [d.model_dump() for d in defense],
            "confidence_threshold": confidence_threshold,
        }),
        response_format={"type": "json_object"},
    )
    judgements = []
    for item in result.get("verdicts", []):
        verdict_str = item.get("verdict", "unsupported")
        try:
            verdict = ClaimVerdict(verdict_str)
        except ValueError:
            verdict = ClaimVerdict.UNSUPPORTED
        judgements.append(ClaimJudgement(
            claim_id=item["claim_id"],
            verdict=verdict,
            confidence=item.get("confidence", 0.0),
            supporting_evidence_ids=item.get("supporting_evidence_ids", []),
            contradicting_evidence_ids=item.get("contradicting_evidence_ids", []),
            explanation=item.get("explanation", ""),
            missing_evidence=item.get("missing_evidence", ""),
            recommended_action=item.get("recommended_action", ""),
        ))
    return judgements


async def run_contradiction_analyst(
    run: ResearchRun,
    claims: list[AtomicClaim],
    evidence: list[Evidence],
) -> list[Contradiction]:
    """Detect contradictions across sources."""
    claims_data = [
        {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids}
        for c in claims
    ]
    ev_data = [
        {"id": e.id, "passage": e.passage, "source_id": e.source_id}
        for e in evidence
    ]
    result = await mesh.complete(
        agent_name="contradiction_analyst",
        system_prompt=prompts.CONTRADICTION_ANALYST_PROMPT,
        user_prompt=json.dumps({"claims": claims_data, "evidence": ev_data}),
        response_format={"type": "json_object"},
    )
    contradictions = []
    for item in result.get("contradictions", []):
        try:
            ctype = ContradictionType(item.get("type", "definition"))
        except ValueError:
            ctype = ContradictionType.DEFINITION
        try:
            severity = ContradictionSeverity(item.get("severity", "medium"))
        except ValueError:
            severity = ContradictionSeverity.MEDIUM
        try:
            resolution = ContradictionResolution(item.get("resolution", "unresolved"))
        except ValueError:
            resolution = ContradictionResolution.UNRESOLVED
        contradictions.append(Contradiction(
            topic=item.get("topic", ""),
            claim_a=item.get("claim_a", ""),
            claim_b=item.get("claim_b", ""),
            evidence_a=item.get("evidence_a", []),
            evidence_b=item.get("evidence_b", []),
            type=ctype,
            severity=severity,
            resolution=resolution,
            explanation=item.get("explanation", ""),
        ))
    return contradictions


async def run_coverage_analyst(
    run: ResearchRun,
    subquestions: list[SubQuestion],
    evidence: list[Evidence],
    judgements: list[ClaimJudgement],
    contradictions: list[Contradiction],
) -> list[CoverageEntry]:
    """Score coverage per subquestion."""
    sq_data = [{"id": s.id, "text": s.text} for s in subquestions]
    ev_data = [
        {"id": e.id, "subquestion_id": e.subquestion_id, "source_id": e.source_id}
        for e in evidence
    ]
    result = await mesh.complete(
        agent_name="coverage_analyst",
        system_prompt=prompts.COVERAGE_ANALYST_PROMPT,
        user_prompt=json.dumps({
            "subquestions": sq_data,
            "evidence": ev_data,
            "judgement_count": len(judgements),
            "contradiction_count": len(contradictions),
        }),
        response_format={"type": "json_object"},
    )
    entries = []
    for item in result.get("coverage", []):
        try:
            status = CoverageStatus(item.get("status", "red"))
        except ValueError:
            status = CoverageStatus.RED
        entries.append(CoverageEntry(
            subquestion_id=item.get("subquestion_id", ""),
            subquestion_text=item.get("subquestion_text", ""),
            evidence_count=item.get("evidence_count", 0),
            source_count=item.get("source_count", 0),
            primary_source_count=item.get("primary_source_count", 0),
            verified_claim_count=item.get("verified_claim_count", 0),
            contradiction_count=item.get("contradiction_count", 0),
            coverage_score=item.get("coverage_score", 0.0),
            status=status,
        ))
    return entries


async def run_synthesizer(
    run: ResearchRun,
    supported_claims: list[AtomicClaim],
    evidence: list[Evidence],
    contradictions: list[Contradiction],
    subquestions: list[SubQuestion],
) -> str:
    """Synthesize final report from verified claims only."""
    claims_data = [
        {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids,
         "subquestion_id": c.subquestion_id}
        for c in supported_claims
    ]
    ev_data = [
        {"id": e.id, "passage": e.passage, "source_id": e.source_id}
        for e in evidence
    ]
    contra_data = [c.model_dump() for c in contradictions if c.resolution == ContradictionResolution.UNRESOLVED]
    sq_data = [{"id": s.id, "text": s.text} for s in subquestions]

    result = await mesh.complete(
        agent_name="synthesizer",
        system_prompt=prompts.SYNTHESIZER_PROMPT,
        user_prompt=json.dumps({
            "question": run.question,
            "supported_claims": claims_data,
            "evidence": ev_data,
            "unresolved_contradictions": contra_data,
            "subquestions": sq_data,
        }),
        response_format={"type": "json_object"},
    )
    return result.get("report", "")
