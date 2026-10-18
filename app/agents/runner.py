"""Agent runner — calls each agent through MeshGateway with typed I/O."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents import prompts
from app.core.config import settings
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
    covered = {query.subquestion_id for query in queries}
    for subquestion in subquestions:
        if subquestion.id not in covered:
            queries.append(SearchQuery(
                subquestion_id=subquestion.id,
                query=f"{subquestion.text} authoritative source",
                source_preference="primary",
            ))
    return queries


async def run_researcher(
    run: ResearchRun,
    source_contents: list[dict[str, str]],
    subquestions: list[SubQuestion],
) -> list[Evidence]:
    """Extract evidence from source content."""
    sq_data = [{"id": s.id, "text": s.text} for s in subquestions]
    evidence_list = []
    source_text = {item["source_id"]: item["content"] for item in source_contents}

    def normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().casefold()

    for source in source_contents:
        result = await mesh.complete(
            agent_name="researcher",
            system_prompt=prompts.RESEARCHER_PROMPT,
            user_prompt=json.dumps({"subquestions": sq_data, "sources": [source]}),
            response_format={"type": "json_object"},
        )
        for item in result.get("evidence", [])[:6]:
            source_id = item.get("source_id", "")
            passage = item.get("passage", "")
            if not source_id or not passage:
                continue
            if normalize(passage) not in normalize(source_text.get(source_id, "")):
                continue
            e = Evidence(
                source_id=source_id,
                subquestion_id=item.get("subquestion_id", ""),
                passage=passage,
                relevance=item.get("relevance", 0.5),
            )
            e.compute_hash()
            evidence_list.append(e)
    return evidence_list


async def run_source_critic(
    run: ResearchRun, sources: list[dict],
) -> dict[str, dict]:
    """Score source trustworthiness."""
    scores = {}
    for start in range(0, len(sources), 3):
        batch = sources[start:start + 3]
        result = await mesh.complete(
            agent_name="source_critic",
            system_prompt=prompts.SOURCE_CRITIC_PROMPT,
            user_prompt=json.dumps({"sources": batch}),
            response_format={"type": "json_object"},
        )
        batch_ids = {source["source_id"] for source in batch}
        for item in result.get("scores", []):
            if item.get("source_id") not in batch_ids:
                continue
            try:
                trust_score = max(0.0, min(1.0, float(item.get("trust_score", 0.5))))
            except (TypeError, ValueError):
                trust_score = 0.0
            scores[item["source_id"]] = {
                "trust_score": trust_score,
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
        user_prompt=json.dumps({
            "evidence": ev_data,
            "subquestions": sq_data,
            "max_claims": min(settings.max_claims, 12),
        }),
        response_format={"type": "json_object"},
    )
    claims = []
    valid_evidence_ids = {e.id for e in evidence}
    for item in result.get("claims", [])[: min(settings.max_claims, 12)]:
        evidence_ids = [eid for eid in item.get("evidence_ids", []) if eid in valid_evidence_ids]
        if not evidence_ids:
            continue
        c = AtomicClaim(
            text=item["text"],
            evidence_ids=evidence_ids,
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
    args = []
    evidence_by_id = {item.id: item for item in evidence}
    for offset in range(0, len(claims), 3):
        claim_batch = claims[offset: offset + 3]
        evidence_ids = {eid for claim in claim_batch for eid in claim.evidence_ids}
        result = await mesh.complete(
            agent_name="prosecutor",
            system_prompt=prompts.PROSECUTOR_PROMPT,
            user_prompt=json.dumps({
                "claims": [
                    {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids}
                    for c in claim_batch
                ],
                "evidence": [
                    {"id": evidence_by_id[eid].id, "passage": evidence_by_id[eid].passage,
                     "source_id": evidence_by_id[eid].source_id}
                    for eid in evidence_ids if eid in evidence_by_id
                ],
            }),
            response_format={"type": "json_object"},
        )
        valid_claim_ids = {claim.id for claim in claim_batch}
        for item in result.get("arguments", []):
            if item.get("claim_id") not in valid_claim_ids:
                continue
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
    defs = []
    evidence_by_id = {item.id: item for item in evidence}
    for offset in range(0, len(claims), 3):
        claim_batch = claims[offset: offset + 3]
        evidence_ids = {eid for claim in claim_batch for eid in claim.evidence_ids}
        result = await mesh.complete(
            agent_name="defense",
            system_prompt=prompts.DEFENSE_PROMPT,
            user_prompt=json.dumps({
                "claims": [
                    {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids}
                    for c in claim_batch
                ],
                "evidence": [
                    {"id": evidence_by_id[eid].id, "passage": evidence_by_id[eid].passage,
                     "source_id": evidence_by_id[eid].source_id}
                    for eid in evidence_ids if eid in evidence_by_id
                ],
            }),
            response_format={"type": "json_object"},
        )
        valid_claim_ids = {claim.id for claim in claim_batch}
        for item in result.get("defenses", []):
            if item.get("claim_id") not in valid_claim_ids:
                continue
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
    judgements = []
    claims_by_id = {claim.id: claim for claim in claims}
    for offset in range(0, len(claims), 3):
        claim_batch = claims[offset: offset + 3]
        claim_ids = {claim.id for claim in claim_batch}
        result = await mesh.complete(
            agent_name="judge",
            system_prompt=prompts.JUDGE_PROMPT,
            user_prompt=json.dumps({
                "claims": [{"id": c.id, "text": c.text} for c in claim_batch],
                "prosecution": [a.model_dump() for a in prosecution if a.claim_id in claim_ids],
                "defense": [d.model_dump() for d in defense if d.claim_id in claim_ids],
                "confidence_threshold": confidence_threshold,
            }),
            response_format={"type": "json_object"},
        )
        for item in result.get("verdicts", []):
            if item.get("claim_id") not in claim_ids:
                continue
            verdict_str = item.get("verdict", "unsupported")
            try:
                verdict = ClaimVerdict(verdict_str)
            except ValueError:
                verdict = ClaimVerdict.UNSUPPORTED
            confidence = item.get("confidence", 0.0)
            claim = claims_by_id[item["claim_id"]]
            supporting_ids = [
                eid for eid in item.get("supporting_evidence_ids", [])
                if eid in claim.evidence_ids
            ]
            if verdict == ClaimVerdict.SUPPORTED and (
                confidence < confidence_threshold or not supporting_ids
            ):
                verdict = ClaimVerdict.UNSUPPORTED
            judgements.append(ClaimJudgement(
                claim_id=item["claim_id"],
                verdict=verdict,
                confidence=confidence,
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=item.get("contradicting_evidence_ids", []),
                explanation=item.get("explanation", ""),
                missing_evidence=item.get("missing_evidence", ""),
                recommended_action=item.get("recommended_action", ""),
            ))
        returned_ids = {
            judgement.claim_id for judgement in judgements if judgement.claim_id in claim_ids
        }
        for missing_id in claim_ids - returned_ids:
            judgements.append(ClaimJudgement(
                claim_id=missing_id,
                verdict=ClaimVerdict.UNSUPPORTED,
                confidence=0.0,
                explanation="Judge omitted this claim from its structured response.",
                missing_evidence="No complete verdict returned.",
                recommended_action="needs_more_research",
            ))
    return judgements


async def run_contradiction_analyst(
    run: ResearchRun,
    claims: list[AtomicClaim],
    evidence: list[Evidence],
) -> list[Contradiction]:
    """Detect contradictions across sources."""
    contradictions = []
    evidence_by_id = {item.id: item for item in evidence}
    claims_by_subquestion: dict[str, list[AtomicClaim]] = {}
    for claim in claims:
        claims_by_subquestion.setdefault(claim.subquestion_id or "unassigned", []).append(claim)

    for related_claims in claims_by_subquestion.values():
        for offset in range(0, len(related_claims), 6):
            claim_batch = related_claims[offset: offset + 6]
            evidence_ids = {eid for claim in claim_batch for eid in claim.evidence_ids}
            result = await mesh.complete(
                agent_name="contradiction_analyst",
                system_prompt=prompts.CONTRADICTION_ANALYST_PROMPT,
                user_prompt=json.dumps({
                    "claims": [
                        {"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids}
                        for c in claim_batch
                    ],
                    "evidence": [
                        {"id": evidence_by_id[eid].id, "passage": evidence_by_id[eid].passage,
                         "source_id": evidence_by_id[eid].source_id}
                        for eid in evidence_ids if eid in evidence_by_id
                    ],
                }),
                response_format={"type": "json_object"},
            )
            for item in result.get("contradictions", [])[:3]:
                valid_evidence_a = [eid for eid in item.get("evidence_a", []) if eid in evidence_ids]
                valid_evidence_b = [eid for eid in item.get("evidence_b", []) if eid in evidence_ids]
                if not valid_evidence_a or not valid_evidence_b:
                    continue
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
                    evidence_a=valid_evidence_a,
                    evidence_b=valid_evidence_b,
                    type=ctype,
                    severity=severity,
                    resolution=resolution,
                    explanation=item.get("explanation", "")[:300],
                ))

    unique = {}
    for contradiction in contradictions:
        key = (contradiction.topic.casefold(), contradiction.claim_a.casefold(), contradiction.claim_b.casefold())
        unique.setdefault(key, contradiction)
    contradictions = list(unique.values())
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
