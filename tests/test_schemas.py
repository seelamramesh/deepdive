"""Tests for Pydantic schemas and data model."""

import pytest
from app.models.schemas import (
    AtomicClaim,
    ClaimJudgement,
    ClaimVerdict,
    Contradiction,
    ContradictionType,
    CoverageEntry,
    CoverageStatus,
    Evidence,
    ResearchRun,
    RunState,
    Source,
    SubQuestion,
    VerificationCertificate,
)


class TestResearchRun:
    def test_create_run(self):
        run = ResearchRun(question="Test question?")
        assert run.question == "Test question?"
        assert run.current_state == RunState.START
        assert run.research_round == 0
        assert len(run.id) == 16

    def test_state_transition(self):
        run = ResearchRun(question="Test")
        run.transition(RunState.PLAN, "Starting plan")
        assert run.current_state == RunState.PLAN
        assert len(run.state_transitions) == 1
        assert run.state_transitions[0].from_state == RunState.START
        assert run.state_transitions[0].to_state == RunState.PLAN

    def test_supported_claims(self):
        run = ResearchRun(question="Test")
        run.claims = [
            AtomicClaim(id="c1", text="Claim 1", evidence_ids=["e1"]),
            AtomicClaim(id="c2", text="Claim 2", evidence_ids=["e2"]),
        ]
        run.judgements = [
            ClaimJudgement(
                claim_id="c1",
                verdict=ClaimVerdict.SUPPORTED,
                confidence=0.9,
                supporting_evidence_ids=["e1"],
            ),
            ClaimJudgement(claim_id="c2", verdict=ClaimVerdict.UNSUPPORTED, confidence=0.3),
        ]
        supported = run.supported_claims()
        assert len(supported) == 1
        assert supported[0].id == "c1"

    def test_supported_claims_enforces_confidence(self):
        run = ResearchRun(question="Test")
        run.claims = [AtomicClaim(id="c1", text="Claim", evidence_ids=["e1"])]
        run.judgements = [ClaimJudgement(
            claim_id="c1",
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.6,
            supporting_evidence_ids=["e1"],
        )]
        assert run.supported_claims(0.7) == []

    def test_get_evidence_by_id(self):
        run = ResearchRun(question="Test")
        run.evidence = [Evidence(id="e1", source_id="s1", passage="test passage")]
        assert run.get_evidence_by_id("e1") is not None
        assert run.get_evidence_by_id("e999") is None


class TestEvidence:
    def test_compute_hash(self):
        ev = Evidence(id="e1", source_id="s1", passage="test passage")
        ev.compute_hash()
        assert ev.passage_hash != ""
        # Same passage = same hash
        ev2 = Evidence(id="e2", source_id="s1", passage="test passage")
        ev2.compute_hash()
        assert ev.passage_hash == ev2.passage_hash


class TestClaimVerdict:
    def test_enum_values(self):
        assert ClaimVerdict.SUPPORTED.value == "supported"
        assert ClaimVerdict.UNSUPPORTED.value == "unsupported"
        assert ClaimVerdict.CONTRADICTED.value == "contradicted"
        assert ClaimVerdict.PARTIALLY_SUPPORTED.value == "partially_supported"


class TestCoverageEntry:
    def test_coverage_status(self):
        green = CoverageEntry(
            subquestion_id="sq1", coverage_score=0.8, status=CoverageStatus.GREEN
        )
        red = CoverageEntry(
            subquestion_id="sq2", coverage_score=0.2, status=CoverageStatus.RED
        )
        assert green.status == CoverageStatus.GREEN
        assert red.status == CoverageStatus.RED


class TestContradiction:
    def test_contradiction_types(self):
        c = Contradiction(
            topic="Market size",
            claim_a="$45B",
            claim_b="$52B",
            type=ContradictionType.NUMERIC,
        )
        assert c.type == ContradictionType.NUMERIC


class TestVerificationCertificate:
    def test_certificate_fields(self):
        cert = VerificationCertificate(
            run_id="test",
            original_question="Test?",
            source_count=5,
            evidence_count=10,
            drafted_claim_count=8,
            supported_claim_count=6,
            rejected_claim_count=2,
            groundedness_rate=0.75,
        )
        assert cert.groundedness_rate == 0.75
        assert cert.rejected_claim_count == 2
