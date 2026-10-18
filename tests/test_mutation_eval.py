from app.models.schemas import AtomicClaim, ClaimJudgement, ClaimVerdict, Evidence, ResearchRun
from scripts.run_mutation_eval import build_eval_artifacts


def test_build_eval_artifacts_uses_supported_claims_and_is_bounded():
    run = ResearchRun(question="A sufficiently detailed research question")
    run.evidence = [
        Evidence(id="e1", source_id="s1", subquestion_id="sq1", passage="About 20 percent in 2025."),
        Evidence(id="e2", source_id="s2", subquestion_id="sq2", passage="Unrelated evidence."),
    ]
    run.claims = [AtomicClaim(
        id="c1",
        text="About 20 percent in 2025.",
        evidence_ids=["e1"],
        subquestion_id="sq1",
    )]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["e1"],
    )]

    cases, claims, evidence = build_eval_artifacts(run, limit=3)

    assert len(cases) == len(claims) == len(evidence) == 3
    assert {case["type"] for case in cases} == {
        "original",
        "unrelated_swap",
        "inflated_statistic",
    }
    assert all(claim.evidence_ids == [item.id] for claim, item in zip(claims, evidence))
