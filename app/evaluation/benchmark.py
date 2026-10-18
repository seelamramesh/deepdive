"""Benchmark questions and citation mutation test."""

from __future__ import annotations

from app.models.schemas import AtomicClaim, ClaimJudgement, ClaimVerdict, Evidence

# ── 10 Benchmark Questions ─────────────────────────────────────────────

BENCHMARK_QUESTIONS = [
    {
        "id": "bq01",
        "category": "current_market",
        "question": "What are the main risks of investing in the EV battery market in 2026?",
        "expected_properties": ["mentions lithium supply", "cites recent data", "identifies multiple risk types"],
    },
    {
        "id": "bq02",
        "category": "scientific",
        "question": "What is the current scientific consensus on the effectiveness of mRNA vaccines for COVID-19?",
        "expected_properties": ["cites peer-reviewed studies", "mentions efficacy rates", "addresses variants"],
    },
    {
        "id": "bq03",
        "category": "policy",
        "question": "What are the key arguments for and against universal basic income?",
        "expected_properties": ["presents both sides", "cites pilot studies", "addresses economic impact"],
    },
    {
        "id": "bq04",
        "category": "historical",
        "question": "What were the primary causes of the 2008 financial crisis?",
        "expected_properties": ["mentions subprime mortgages", "cites regulatory failures", "discusses systemic risk"],
    },
    {
        "id": "bq05",
        "category": "disputed",
        "question": "Is nuclear energy a viable solution to climate change?",
        "expected_properties": ["addresses safety concerns", "mentions cost factors", "presents opposing views"],
    },
    {
        "id": "bq06",
        "category": "conflicting_statistics",
        "question": "What is the global rate of deforestation and is it increasing or decreasing?",
        "expected_properties": ["cites specific numbers", "notes data source differences", "addresses regional variation"],
    },
    {
        "id": "bq07",
        "category": "outdated_source",
        "question": "What is the current state of quantum computing capabilities?",
        "expected_properties": ["uses recent sources", "mentions qubit counts", "addresses practical applications"],
    },
    {
        "id": "bq08",
        "category": "misleading_headline",
        "question": "Has artificial general intelligence been achieved?",
        "expected_properties": ["distinguishes hype from reality", "defines AGI clearly", "cites expert opinions"],
    },
    {
        "id": "bq09",
        "category": "unsupported_forecast",
        "question": "Will the global economy enter a recession in the next 12 months?",
        "expected_properties": ["presents forecasts with caveats", "cites multiple analysts", "acknowledges uncertainty"],
    },
    {
        "id": "bq10",
        "category": "insufficient_evidence",
        "question": "What are the long-term health effects of microplastics in drinking water?",
        "expected_properties": ["acknowledges limited research", "cites available studies", "notes knowledge gaps"],
    },
]


# ── Citation Mutation Test ──────────────────────────────────────────────

def create_mutation_test_cases(
    claims: list[AtomicClaim],
    evidence: list[Evidence],
    judgements: list[ClaimJudgement] | None = None,
) -> list[dict]:
    """Create mutation test cases from accepted claim/evidence pairs.

    Mutations:
    1. Original (positive control)
    2. Swap citation to unrelated passage
    3. Swap citation to topically similar but non-supporting
    4. Remove qualifying language
    5. Inflate statistic or change date
    """
    cases = []
    ev_map = {e.id: e for e in evidence}
    judgement_by_claim = {
        judgement.claim_id: judgement for judgement in (judgements or [])
    }

    for claim in claims:
        if not claim.evidence_ids:
            continue

        judgement = judgement_by_claim.get(claim.id)
        approved_ids = [
            evidence_id for evidence_id in (
                judgement.supporting_evidence_ids if judgement else claim.evidence_ids
            )
            if evidence_id in claim.evidence_ids and evidence_id in ev_map
        ]
        if not approved_ids:
            continue
        primary_eid = approved_ids[0]
        primary_ev = ev_map[primary_eid]
        approved_passage = "\n\n".join(ev_map[evidence_id].passage for evidence_id in approved_ids)

        # 1. Original
        cases.append({
            "type": "original",
            "claim": claim.text,
            "evidence_id": primary_eid,
            "passage": approved_passage,
            "expected_verdict": "supported",
        })

        # 2. Swap with unrelated
        unrelated = [e for e in evidence if e.id not in approved_ids and e.subquestion_id != claim.subquestion_id]
        if unrelated:
            cases.append({
                "type": "unrelated_swap",
                "claim": claim.text,
                "evidence_id": unrelated[0].id,
                "passage": unrelated[0].passage,
                "expected_verdict": "unsupported",
            })

        # 3. Topically similar but non-supporting
        similar = [e for e in evidence if e.id not in approved_ids and e.subquestion_id == claim.subquestion_id]
        if similar:
            cases.append({
                "type": "similar_swap",
                "claim": claim.text,
                "evidence_id": similar[0].id,
                "passage": similar[0].passage,
                "expected_verdict": "unsupported",
            })

        # 4. Removed qualifier
        mutated_text = claim.text.replace("approximately ", "exactly ").replace("about ", "precisely ").replace("roughly ", "exactly ")
        if mutated_text != claim.text:
            cases.append({
                "type": "qualifier_removed",
                "claim": mutated_text,
                "evidence_id": primary_eid,
                "passage": approved_passage,
                "expected_verdict": "partially_supported",
            })

        # 5. Inflated statistic
        import re
        nums = re.findall(r"\d+\.?\d*", claim.text)
        if nums:
            inflated = claim.text.replace(nums[0], str(float(nums[0]) * 2.5), 1)
            cases.append({
                "type": "inflated_statistic",
                "claim": inflated,
                "evidence_id": primary_eid,
                "passage": approved_passage,
                "expected_verdict": "contradicted",
            })

    return cases


def compute_mutation_metrics(results: list[dict]) -> dict:
    """Compute metrics from mutation test results."""
    total = len(results)
    if total == 0:
        return {"total": 0}

    originals = [r for r in results if r["type"] == "original"]
    mutations = [r for r in results if r["type"] != "original"]

    original_correct = sum(1 for r in originals if r.get("actual_verdict") == r["expected_verdict"])
    mutation_rejected = sum(
        1 for r in mutations
        if r.get("actual_verdict") in ("unsupported", "contradicted", "partially_supported")
    )
    false_accepts = sum(
        1 for r in mutations
        if r.get("actual_verdict") == "supported"
    )

    return {
        "total_cases": total,
        "original_count": len(originals),
        "mutation_count": len(mutations),
        "supported_claim_recall": original_correct / max(len(originals), 1),
        "mutation_rejection_rate": mutation_rejected / max(len(mutations), 1),
        "false_acceptance_rate": false_accepts / max(len(mutations), 1),
    }


def evaluate_run(run) -> dict:
    """Compute deterministic, auditable quality metrics for a completed run."""
    evidence_ids = {item.id for item in run.evidence}
    source_ids = {item.id for item in run.sources}
    supported = run.supported_claims()
    supported_ids = {item.id for item in supported}

    judgement_by_claim = {judgement.claim_id: judgement for judgement in run.judgements}
    citation_links = [
        evidence_id
        for claim in supported
        for evidence_id in judgement_by_claim[claim.id].supporting_evidence_ids
        if evidence_id in claim.evidence_ids
    ]
    valid_citation_links = sum(
        1 for evidence_id in citation_links if evidence_id in evidence_ids
    )
    evidence_with_sources = sum(
        1 for item in run.evidence if item.source_id in source_ids
    )
    rejected_claims = [
        claim for claim in run.claims if claim.id not in supported_ids
    ]
    agent_names = sorted({call.agent for call in run.agent_calls if call.success})

    return {
        "run_id": run.id,
        "question": run.question,
        "state": run.current_state.value,
        "research_rounds": run.research_round,
        "source_count": len(run.sources),
        "evidence_count": len(run.evidence),
        "claim_count": len(run.claims),
        "supported_claim_count": len(supported),
        "rejected_claim_count": len(rejected_claims),
        "contradiction_count": len(run.contradictions),
        "successful_agent_count": len(agent_names),
        "successful_agents": agent_names,
        "citation_link_count": len(citation_links),
        "valid_citation_link_count": valid_citation_links,
        "citation_integrity_rate": valid_citation_links / max(len(citation_links), 1),
        "evidence_source_integrity_rate": evidence_with_sources / max(len(run.evidence), 1),
        "coverage": {
            status.value: sum(1 for entry in run.coverage if entry.status == status)
            for status in type(run.coverage[0].status)
        } if run.coverage else {},
        "report_nonempty": bool(run.final_report.strip()),
        "error": run.error,
        "warnings": list(run.warnings),
    }
