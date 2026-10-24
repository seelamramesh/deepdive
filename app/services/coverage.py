"""Deterministic coverage counts; qualitative assessments remain heuristic."""
import math

from app.models.schemas import CoverageEntry, CoverageStatus, ResearchRun


def verified_claims_with_sources(run: ResearchRun):
    sources = {source.id for source in run.sources}
    evidence = {item.id for item in run.evidence if item.source_id in sources}
    verdicts = {item.claim_id: item for item in run.judgements}
    return [claim for claim in run.supported_claims(run.confidence_threshold)
            if any(eid in evidence and eid in claim.evidence_ids for eid in verdicts[claim.id].supporting_evidence_ids)]


def derive_coverage(run: ResearchRun, assessments: list[dict]) -> list[CoverageEntry]:
    sources = {source.id: source for source in run.sources}
    evidence = {item.id: item for item in run.evidence if item.source_id in sources}
    verified = verified_claims_with_sources(run)
    by_id = {item.get('subquestion_id'): item for item in assessments if isinstance(item, dict)}
    entries = []
    for subquestion in run.subquestions:
        item = by_id.get(subquestion.id, {})
        passages = {eid: ev for eid, ev in evidence.items() if ev.subquestion_id == subquestion.id}
        source_ids = {ev.source_id for ev in passages.values()}
        accepted = len({claim.id for claim in verified if claim.subquestion_id == subquestion.id})
        try:
            status = CoverageStatus(item.get('status', 'red'))
        except ValueError:
            status = CoverageStatus.RED
        if not passages:
            status = CoverageStatus.RED
        elif not accepted and status == CoverageStatus.GREEN:
            status = CoverageStatus.YELLOW
        try:
            score = float(item.get('coverage_score', 0.0))
            score = max(0.0, min(1.0, score)) if math.isfinite(score) and passages else 0.0
        except (TypeError, ValueError):
            score = 0.0
        entries.append(CoverageEntry(
            subquestion_id=subquestion.id, subquestion_text=subquestion.text,
            evidence_count=len(passages), source_count=len(source_ids),
            primary_source_count=sum(sources[sid].trust_factors.get('primary_source') is True for sid in source_ids),
            verified_claim_count=accepted,
            contradiction_count=sum(bool(set(pair.evidence_a + pair.evidence_b) & passages.keys()) for pair in run.contradictions),
            coverage_score=score, status=status,
        ))
    return entries
