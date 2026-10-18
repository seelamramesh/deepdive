"""Tests for evaluation and citation mutation."""

import pytest
from app.evaluation.benchmark import (
    BENCHMARK_QUESTIONS,
    create_mutation_test_cases,
    compute_mutation_metrics,
    evaluate_run,
)
from app.models.schemas import ClaimJudgement, ClaimVerdict, ResearchRun, RunState


class TestBenchmark:
    def test_has_10_questions(self):
        assert len(BENCHMARK_QUESTIONS) == 10

    def test_all_have_required_fields(self):
        for q in BENCHMARK_QUESTIONS:
            assert "id" in q
            assert "category" in q
            assert "question" in q
            assert "expected_properties" in q
            assert len(q["expected_properties"]) >= 1

    def test_categories_are_distinct(self):
        categories = [q["category"] for q in BENCHMARK_QUESTIONS]
        assert len(set(categories)) == 10


class TestCitationMutation:
    def test_creates_mutations(self, sample_claims, sample_evidence):
        cases = create_mutation_test_cases(sample_claims, sample_evidence)
        assert len(cases) >= 3  # At least one original per claim with evidence
        types = {c["type"] for c in cases}
        assert "original" in types

    def test_mutation_metrics_empty(self):
        metrics = compute_mutation_metrics([])
        assert metrics["total"] == 0

    def test_mutation_metrics_correct(self):
        results = [
            {"type": "original", "expected_verdict": "supported", "actual_verdict": "supported"},
            {"type": "unrelated_swap", "expected_verdict": "unsupported", "actual_verdict": "unsupported"},
            {"type": "similar_swap", "expected_verdict": "unsupported", "actual_verdict": "supported"},
        ]
        metrics = compute_mutation_metrics(results)
        assert metrics["total_cases"] == 3
        assert metrics["supported_claim_recall"] == 1.0
        assert metrics["mutation_rejection_rate"] == 0.5
        assert metrics["false_acceptance_rate"] == 0.5


def test_evaluate_run_measures_persisted_artifacts(sample_claims, sample_evidence):
    run = ResearchRun(question="What evidence supports this sufficiently detailed question?")
    run.current_state = RunState.END
    run.claims = sample_claims
    run.evidence = sample_evidence
    run.judgements = [
        ClaimJudgement(
            claim_id=sample_claims[0].id,
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.9,
            supporting_evidence_ids=[sample_evidence[0].id],
        )
    ]
    run.final_report = "# Verified report"

    metrics = evaluate_run(run)

    assert metrics["state"] == "END"
    assert metrics["supported_claim_count"] == 1
    assert metrics["rejected_claim_count"] == len(sample_claims) - 1
    assert metrics["citation_integrity_rate"] == 1.0
    assert metrics["report_nonempty"] is True
