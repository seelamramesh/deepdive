import pytest

from app.models.schemas import (
    AtomicClaim,
    ClaimJudgement,
    ClaimVerdict,
    CoverageEntry,
    DefenseArgument,
    Evidence,
    ProsecutorArgument,
    ResearchRun,
    SearchQuery,
    Source,
    SubQuestion,
    _hash,
)
from app.services.orchestrator import (
    _build_certificate,
    _insufficient_evidence_report,
    _queries_for_round,
    _trusted_evidence,
    _verified_claim_report,
    _verify_report_citations,
    run_research,
)


def test_queries_rotate_between_rounds():
    queries = [
        SearchQuery(id="q1", subquestion_id="s1", query="one"),
        SearchQuery(id="q2", subquestion_id="s2", query="two"),
        SearchQuery(id="q3", subquestion_id="s3", query="three"),
    ]

    assert [q.id for q in _queries_for_round(queries, 1, 1)] == ["q1"]
    assert [q.id for q in _queries_for_round(queries, 2, 1)] == ["q2"]
    assert [q.id for q in _queries_for_round(queries, 3, 1)] == ["q3"]


def test_query_selection_stays_bounded_and_wraps():
    queries = [
        SearchQuery(id="q1", subquestion_id="s1", query="one"),
        SearchQuery(id="q2", subquestion_id="s1", query="one alternate"),
        SearchQuery(id="q3", subquestion_id="s2", query="two"),
        SearchQuery(id="q4", subquestion_id="s3", query="three"),
    ]

    assert [q.id for q in _queries_for_round(queries, 1, 2)] == ["q1", "q3"]
    assert [q.id for q in _queries_for_round(queries, 2, 2)] == ["q4", "q1"]
    assert _queries_for_round([], 1, 2) == []


def test_empty_verified_result_is_explicit_not_blank():
    run = ResearchRun(question="Dallas housing market forecast for 2027")
    run.research_round = 3

    report = _insufficient_evidence_report(run)

    assert "Insufficient verified evidence" in report
    assert "No market forecast should be inferred" in report
    assert "Sources successfully retrieved: 0" in report


def test_report_verifier_removes_uncited_and_orphan_factual_lines():
    run = ResearchRun(question="question")
    run.evidence = [Evidence(id="e1", source_id="s1", passage="Exact passage")]
    run.claims = [AtomicClaim(id="c1", text="Supported", evidence_ids=["e1"])]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["e1"],
    )]
    run.final_report = (
        "# Report\n\n"
        "Valid fact [claim:c1] [evidence:e1]\n"
        "Uncited fabricated fact\n"
        "Orphan fact [claim:bad] [evidence:e1]"
    )

    _verify_report_citations(run)

    assert "Valid fact" in run.final_report
    assert "fabricated" not in run.final_report
    assert "Orphan" not in run.final_report


def test_report_verifier_rejects_draft_link_not_approved_by_judge():
    run = ResearchRun(question="question")
    run.evidence = [
        Evidence(id="approved", source_id="s1", passage="Approved passage"),
        Evidence(id="draft-only", source_id="s1", passage="Draft-only passage"),
    ]
    run.claims = [AtomicClaim(
        id="c1",
        text="Supported",
        evidence_ids=["approved", "draft-only"],
    )]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["approved"],
    )]
    run.final_report = (
        "# Report\n\n"
        "Approved fact [claim:c1] [evidence:approved]\n"
        "Unapproved fact [claim:c1] [evidence:draft-only]"
    )

    _verify_report_citations(run)

    assert "Approved fact" in run.final_report
    assert "Unapproved fact" not in run.final_report


def test_certificate_uses_threshold_and_judge_approved_links(monkeypatch):
    monkeypatch.setattr("app.services.orchestrator.settings.confidence_threshold", 0.7)
    run = ResearchRun(question="question")
    run.evidence = [Evidence(id="e1", source_id="s1", passage="Exact passage")]
    run.claims = [
        AtomicClaim(id="high", text="High confidence", evidence_ids=["e1"]),
        AtomicClaim(id="low", text="Low confidence", evidence_ids=["e1"]),
    ]
    run.judgements = [
        ClaimJudgement(
            claim_id="high",
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.9,
            supporting_evidence_ids=["e1"],
        ),
        ClaimJudgement(
            claim_id="low",
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.6,
            supporting_evidence_ids=["e1"],
        ),
    ]

    certificate = _build_certificate(run)

    assert certificate.supported_claim_count == 1
    assert certificate.rejected_claim_count == 1
    assert certificate.groundedness_rate == 0.5
    assert certificate.citation_coverage_rate == 1.0


def test_report_verifier_rebuilds_heading_only_report_from_verified_claims():
    run = ResearchRun(question="Technology outlook")
    run.evidence = [Evidence(id="e1", source_id="s1", passage="Exact passage")]
    run.claims = [AtomicClaim(id="c1", text="Verified fact", evidence_ids=["e1"])]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["e1"],
    )]
    run.final_report = "# Report\n\n## Empty Section\nUnsupported prose"

    _verify_report_citations(run)

    assert "Verified fact [claim:c1] [evidence:e1]" in run.final_report
    assert "Unsupported prose" not in run.final_report


def test_verified_claim_report_uses_only_valid_judgement_links():
    run = ResearchRun(question="Technology outlook")
    run.evidence = [Evidence(id="e1", source_id="s1", passage="Exact passage")]
    run.claims = [AtomicClaim(id="c1", text="Verified fact", evidence_ids=["e1"])]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["e1", "invented"],
    )]

    report = _verified_claim_report(run, run.supported_claims())

    assert "Verified fact [claim:c1] [evidence:e1]" in report
    assert "invented" not in report
    assert "Synthesizer output was unavailable" in report


def test_report_verifier_removes_empty_sections_but_keeps_populated_sections():
    run = ResearchRun(question="Technology outlook")
    run.evidence = [Evidence(id="e1", source_id="s1", passage="Exact passage")]
    run.claims = [AtomicClaim(id="c1", text="Verified fact", evidence_ids=["e1"])]
    run.judgements = [ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["e1"],
    )]
    run.final_report = (
        "# Report\n\n## Populated\nVerified fact [claim:c1] [evidence:e1]\n\n"
        "## Empty\n\n## Also Empty\n"
    )

    _verify_report_citations(run)

    assert "## Populated" in run.final_report
    assert "## Empty" not in run.final_report
    assert "## Also Empty" not in run.final_report


def test_trusted_evidence_excludes_sources_below_threshold(monkeypatch):
    monkeypatch.setattr("app.services.orchestrator.settings.min_source_trust", 0.4)
    run = ResearchRun(question="question")
    run.sources = [
        Source(id="low", url="https://low.example", title="Low", trust_score=0.39),
        Source(id="edge", url="https://edge.example", title="Edge", trust_score=0.4),
    ]
    run.evidence = [
        Evidence(id="e-low", source_id="low", passage="Low evidence"),
        Evidence(id="e-edge", source_id="edge", passage="Edge evidence"),
    ]

    assert [item.id for item in _trusted_evidence(run)] == ["e-edge"]


@pytest.mark.asyncio
async def test_late_failure_returns_checkpoint_report_with_warning(monkeypatch):
    subquestion = SubQuestion(id="sq1", text="Subquestion")
    source = Source(id="s1", url="https://example.com", title="Source",
                    content_snapshot="Exact fact", content_hash=_hash("Exact fact"))
    evidence = Evidence(id="e1", source_id="s1", subquestion_id="sq1", passage="Exact fact")
    claim = AtomicClaim(id="c1", text="Exact fact", evidence_ids=["e1"], subquestion_id="sq1")
    judgement = ClaimJudgement(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["e1"],
    )
    saved = []

    async def save(run):
        saved.append(run.model_copy(deep=True))

    monkeypatch.setattr("app.services.orchestrator.run_planner", lambda run: async_value([subquestion]))
    monkeypatch.setattr("app.services.orchestrator.run_search_strategist", lambda run, items: async_value([]))
    monkeypatch.setattr("app.services.orchestrator.fetch_sources", lambda urls: async_value([source]))
    monkeypatch.setattr("app.services.orchestrator.run_researcher", lambda *args: async_value([evidence]))
    monkeypatch.setattr("app.services.orchestrator.run_source_critic", lambda *args: async_value({
        "s1": {"trust_score": 0.8, "factors": {}}
    }))
    monkeypatch.setattr("app.services.orchestrator.run_claim_drafter", lambda *args: async_value([claim]))
    monkeypatch.setattr("app.services.orchestrator.run_prosecutor", lambda *args: async_value([
        ProsecutorArgument(claim_id="c1")
    ]))
    monkeypatch.setattr("app.services.orchestrator.run_defense", lambda *args: async_value([
        DefenseArgument(claim_id="c1")
    ]))
    monkeypatch.setattr("app.services.orchestrator.run_judge", lambda *args: async_value([judgement]))

    async def fail_contradictions(*args):
        raise ValueError("late failure")

    monkeypatch.setattr("app.services.orchestrator.run_contradiction_analyst", fail_contradictions)
    monkeypatch.setattr("app.services.orchestrator.run_synthesizer", lambda *args: async_value(
        "# Report\nExact fact [claim:c1] [evidence:e1]"
    ))
    monkeypatch.setattr("app.services.orchestrator.save_run", save)
    monkeypatch.setattr("app.services.orchestrator.mesh.drain_calls", lambda: [])

    run = await run_research("A sufficiently long research question", ["https://example.com"], max_rounds=1)

    assert run.current_state.value == "END"
    assert run.error is None
    assert any("late failure" in warning for warning in run.warnings)
    assert "Exact fact" in run.final_report
    assert saved[-1].current_state.value == "END"


async def async_value(value):
    return value
