"""Tests for evaluation and citation mutation."""

import pytest
from app.evaluation.benchmark import (
    BENCHMARK_QUESTIONS,
    create_mutation_test_cases,
    compute_mutation_metrics,
)


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
