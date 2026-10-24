"""Agent runner — calls each agent through MeshGateway with typed I/O."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents import prompts
from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.services.coverage import derive_coverage, verified_claims_with_sources
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
    sq_data = [{"id": s.id, "text": s.text, "completion_criteria": s.completion_criteria} for s in subquestions]
    coverage_by_id = {entry.subquestion_id: entry for entry in run.coverage}
    judgement_by_id = {item.claim_id: item for item in run.judgements}
    gap_feedback = []
    if run.research_round > 1:
        for subquestion in subquestions:
            coverage = coverage_by_id.get(subquestion.id)
            failed_claims = []
            for claim in run.claims:
                judgement = judgement_by_id.get(claim.id)
                if claim.subquestion_id != subquestion.id or not judgement:
                    continue
                if judgement.verdict != ClaimVerdict.SUPPORTED:
                    failed_claims.append({
                        "claim_id": claim.id,
                        "text": claim.text,
                        "verdict": judgement.verdict.value,
                        "reason": judgement.explanation,
                        "missing_evidence": judgement.missing_evidence,
                    })
            if coverage is None or coverage.status != CoverageStatus.GREEN or failed_claims:
                gap_feedback.append({
                    "subquestion_id": subquestion.id,
                    "completion_criteria": subquestion.completion_criteria,
                    "coverage_status": coverage.status.value if coverage else "red",
                    "failed_claims": failed_claims[:12],
                })
    previous_queries = {query.query.strip().casefold() for query in run.search_queries}
    search_input = {
        "question": run.question,
        "round": run.research_round,
        "query_budget": settings.max_search_queries_per_round,
        "subquestions": sq_data,
        "gap_feedback": gap_feedback,
        "previous_queries": [query.query for query in run.search_queries],
    }
    run.search_audit.append({"input": search_input})
    result = await mesh.complete(
        agent_name="search_strategist",
        system_prompt=prompts.SEARCH_STRATEGIST_PROMPT,
        user_prompt=json.dumps(search_input),
        response_format={"type": "json_object"},
    )
    queries = []
    valid_subquestion_ids = {subquestion.id for subquestion in subquestions}
    seen_queries = set(previous_queries)
    for item in result.get("queries", []):
        query_text = item.get("query", "")
        if not isinstance(query_text, str) or not query_text.strip():
            continue
        query_key = query_text.strip().casefold()
        if item.get("subquestion_id") not in valid_subquestion_ids or query_key in seen_queries:
            continue
        seen_queries.add(query_key)
        q = SearchQuery(
            subquestion_id=item.get("subquestion_id", ""),
            query=query_text.strip(),
            source_preference=item.get("source_preference", ""),
        )
        queries.append(q)
    covered = {query.subquestion_id for query in queries}
    for subquestion in subquestions:
        if subquestion.id not in covered:
            missing = next((gap for gap in gap_feedback if gap["subquestion_id"] == subquestion.id), None)
            missing_detail = " ".join(
                claim["missing_evidence"] for claim in (missing or {}).get("failed_claims", [])
                if claim["missing_evidence"]
            )
            query_text = " ".join(filter(None, [subquestion.text, missing_detail or subquestion.completion_criteria, "authoritative source"]))
            if query_text.casefold() in seen_queries:
                continue
            seen_queries.add(query_text.casefold())
            queries.append(SearchQuery(
                subquestion_id=subquestion.id,
                query=query_text,
                source_preference="primary",
            ))
    run.search_audit[-1]["planned_queries"] = [query.model_dump() for query in queries]
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
    snapshot_hashes = {item["source_id"]: item.get("snapshot_hash", "") for item in source_contents}

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
                source_snapshot_hash=snapshot_hashes.get(source_id, ""),
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
            user_prompt=json.dumps({"question": run.question, "sources": batch}),
            response_format={"type": "json_object"},
            prompt_version="source-critic-window-v2",
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
    claims_by_id = {claim.id: claim for claim in claims}
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
                supporting_passages=_verified_defense_passages(
                    claims_by_id[item["claim_id"]], item.get("supporting_passages", []), evidence_by_id
                ),
            ))
    return defs


def _verified_defense_passages(claim: AtomicClaim, passages: list, evidence_by_id: dict[str, Evidence]) -> list[dict]:
    """Check quote membership, not semantic entailment. Normalize whitespace only."""
    verified = []
    if not isinstance(passages, list):
        return verified
    for item in passages:
        if not isinstance(item, dict):
            continue
        evidence_id = item.get("evidence_id")
        excerpt = item.get("passage_excerpt")
        if not isinstance(evidence_id, str) or evidence_id not in claim.evidence_ids:
            continue
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None or not isinstance(excerpt, str) or not excerpt.strip():
            continue
        if " ".join(excerpt.split()) in " ".join(evidence.passage.split()):
            verified.append(item)
    return verified


async def run_judge(
    run: ResearchRun,
    claims: list[AtomicClaim],
    prosecution: list[ProsecutorArgument],
    defense: list[DefenseArgument],
    confidence_threshold: float,
    evidence: list[Evidence] | None = None,
) -> list[ClaimJudgement]:
    """Render verdicts on claims."""
    judgements = []
    claims_by_id = {claim.id: claim for claim in claims}
    evidence_by_id = {item.id: item for item in (run.evidence if evidence is None else evidence)}
    for offset in range(0, len(claims), 3):
        claim_batch = claims[offset: offset + 3]
        claim_ids = {claim.id for claim in claim_batch}
        batch_evidence_ids = {eid for claim in claim_batch for eid in claim.evidence_ids if eid in evidence_by_id}
        result = await mesh.complete(
            agent_name="judge",
            system_prompt=prompts.JUDGE_PROMPT,
            user_prompt=json.dumps({
                "claims": [{"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids} for c in claim_batch],
                "evidence": [
                    {"id": eid, "source_id": evidence_by_id[eid].source_id,
                     "passage": evidence_by_id[eid].passage}
                    for eid in sorted(batch_evidence_ids)
                ],
                "prosecution": [a.model_dump() for a in prosecution if a.claim_id in claim_ids],
                "defense": [
                    {"claim_id": d.claim_id, "supporting_passages": _verified_defense_passages(
                        claims_by_id[d.claim_id], d.supporting_passages, evidence_by_id
                    )}
                    for d in defense if d.claim_id in claim_ids
                ],
                "confidence_threshold": confidence_threshold,
            }),
            response_format={"type": "json_object"},
            prompt_version="judge-grounded-v2",
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
                if eid in claim.evidence_ids and eid in evidence_by_id
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
                contradicting_evidence_ids=[
                    eid for eid in item.get("contradicting_evidence_ids", []) if eid in batch_evidence_ids
                ],
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
    """Compare bounded cross-source candidate pairs; disclose incomplete coverage."""
    from itertools import combinations

    evidence_by_id = {item.id: item for item in evidence}
    claims_by_id = {claim.id: claim for claim in claims}
    linked = {claim.id: {evidence_by_id[eid].source_id for eid in claim.evidence_ids
                        if eid in evidence_by_id and evidence_by_id[eid].source_id} for claim in claims}
    remaining = [(a.id, b.id) for a, b in combinations(claims, 2)
                 if any(sa != sb for sa in linked[a.id] for sb in linked[b.id])]
    audit = {"round": run.research_round, "status": "running",
             "claim_linked_source_count": len(set().union(*linked.values())) if linked else 0,
             "eligible_cross_source_pairs": len(remaining), "compared_candidate_pairs": 0,
             "uncompared_candidate_pairs": len(remaining), "rejected_candidates": 0, "batches": []}
    run.contradiction_audit.append(audit)
    contradictions = list(run.contradictions)
    if not remaining:
        audit["status"] = "skipped_single_source" if audit["claim_linked_source_count"] < 2 else "no_cross_source_pairs"
        return contradictions

    for _ in range(settings.max_contradiction_batches):
        if not remaining:
            break
        # Greedily cover pairs, including pairs split across former topic/chunk boundaries.
        batch_ids = list(remaining[0])
        while len(batch_ids) < 6:
            choices = [cid for cid in claims_by_id if cid not in batch_ids]
            scores = {cid: sum(cid in pair and any(other in batch_ids for other in pair if other != cid)
                               for pair in remaining) for cid in choices}
            if not scores or max(scores.values()) == 0:
                break
            batch_ids.append(max(scores, key=scores.get))
        claim_batch = [claims_by_id[cid] for cid in batch_ids]
        evidence_ids = {eid for claim in claim_batch for eid in claim.evidence_ids if eid in evidence_by_id}
        batch_audit = {"claim_ids": batch_ids, "evidence_ids": sorted(evidence_ids), "status": "running", "returned_candidates": 0}
        audit["batches"].append(batch_audit)
        try:
            result = await mesh.complete(
                agent_name="contradiction_analyst",
                system_prompt=prompts.CONTRADICTION_ANALYST_PROMPT,
                user_prompt=json.dumps({
                    "claims": [{"id": c.id, "text": c.text, "evidence_ids": c.evidence_ids,
                                "subquestion_id": c.subquestion_id} for c in claim_batch],
                    "evidence": [{"id": eid, "passage": evidence_by_id[eid].passage,
                                  "source_id": evidence_by_id[eid].source_id} for eid in sorted(evidence_ids)],
                }),
                response_format={"type": "json_object"},
                prompt_version="contradiction-cross-source-v2",
            )
        except Exception:
            batch_audit["status"] = "failed"
            audit["status"] = "failed"
            raise
        batch_audit["status"] = "completed"
        remaining = [pair for pair in remaining if not set(pair) <= set(batch_ids)]
        audit["uncompared_candidate_pairs"] = len(remaining)
        audit["compared_candidate_pairs"] = audit["eligible_cross_source_pairs"] - len(remaining)
        for item in result.get("contradictions", []):
            batch_audit["returned_candidates"] += 1
            a = [eid for eid in item.get("evidence_a", []) if isinstance(eid, str) and eid in evidence_ids]
            b = [eid for eid in item.get("evidence_b", []) if isinstance(eid, str) and eid in evidence_ids]
            if (not a or not b or not any(evidence_by_id[x].source_id != evidence_by_id[y].source_id for x in a for y in b)
                    or not item.get("claim_a") or not item.get("claim_b")):
                audit["rejected_candidates"] += 1
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
                topic=item.get("topic", ""), claim_a=item["claim_a"], claim_b=item["claim_b"],
                evidence_a=a, evidence_b=b, type=ctype, severity=severity, resolution=resolution,
                explanation=item.get("explanation", "")[:300],
            ))
    unique = {}
    for item in contradictions:
        # Count source-pair/type disagreements, independent of generated titles.
        key = (tuple(sorted((tuple(sorted(item.evidence_a)), tuple(sorted(item.evidence_b))))), item.type)
        unique[key] = item
    audit["status"] = "limited_comparison" if remaining else "completed_comparison"
    audit["retained_contradictions"] = len(unique)
    return list(unique.values())


async def run_coverage_analyst(
    run: ResearchRun,
    subquestions: list[SubQuestion],
    evidence: list[Evidence],
    judgements: list[ClaimJudgement],
    contradictions: list[Contradiction],
) -> list[CoverageEntry]:
    """Score coverage per subquestion."""
    sq_data = [{"id": s.id, "text": s.text, "completion_criteria": s.completion_criteria} for s in subquestions]
    snapshot = run.model_copy(update={"subquestions": subquestions, "evidence": evidence,
                                      "judgements": judgements, "contradictions": contradictions})
    verified_claims = verified_claims_with_sources(snapshot)
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
            "verified_claims": [claim.model_dump() for claim in verified_claims],
            "judgement_count": len(judgements),
            "contradiction_count": len(contradictions),
        }),
        response_format={"type": "json_object"},
    )
    return derive_coverage(snapshot, result.get("coverage", []))


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
