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

    for claim in claims:
        if not claim.evidence_ids:
            continue

        primary_eid = claim.evidence_ids[0]
        primary_ev = ev_map.get(primary_eid)
        if not primary_ev:
            continue

        # 1. Original
        cases.append({
            "type": "original",
            "claim": claim.text,
            "evidence_id": primary_eid,
            "passage": primary_ev.passage,
            "expected_verdict": "supported",
        })

        # 2. Swap with unrelated
        unrelated = [e for e in evidence if e.id not in claim.evidence_ids and e.subquestion_id != claim.subquestion_id]
        if unrelated:
            cases.append({
                "type": "unrelated_swap",
                "claim": claim.text,
                "evidence_id": unrelated[0].id,
                "passage": unrelated[0].passage,
                "expected_verdict": "unsupported",
            })

        # 3. Topically similar but non-supporting
        similar = [e for e in evidence if e.id not in claim.evidence_ids and e.subquestion_id == claim.subquestion_id]
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
                "passage": primary_ev.passage,
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
                "passage": primary_ev.passage,
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
