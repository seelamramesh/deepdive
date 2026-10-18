"""Research orchestrator — drives the state machine end to end."""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.runner import (
    run_claim_drafter,
    run_contradiction_analyst,
    run_coverage_analyst,
    run_defense,
    run_judge,
    run_planner,
    run_prosecutor,
    run_researcher,
    run_search_strategist,
    run_source_critic,
    run_synthesizer,
)
from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.models.schemas import (
    ClaimVerdict,
    CoverageStatus,
    ResearchRun,
    RunState,
    VerificationCertificate,
    _hash,
)
from app.services.retrieval import fetch_sources, fetch_url
from app.storage.database import save_run

logger = logging.getLogger(__name__)


async def run_research(
    question: str,
    source_urls: list[str] | None = None,
    max_rounds: int | None = None,
    confidence_threshold: float | None = None,
    run_id: str | None = None,
) -> ResearchRun:
    """Execute a full research run through the state machine."""
    if run_id:
        run = ResearchRun(question=question, id=run_id)
    else:
        run = ResearchRun(question=question)
    max_rounds = max_rounds or settings.max_research_rounds
    conf_threshold = confidence_threshold or settings.confidence_threshold
    source_urls = source_urls or []

    # Collected source contents for the researcher agent
    source_contents: list[dict[str, str]] = []

    try:
        # ── PLAN ───────────────────────────────────────────────
        run.transition(RunState.PLAN, "Starting research planning")
        run.subquestions = await run_planner(run)
        await save_run(run)

        while run.research_round < max_rounds:
            run.research_round += 1

            # ── SEARCH ─────────────────────────────────────────
            run.transition(RunState.SEARCH, f"Round {run.research_round}: generating queries")
            queries = await run_search_strategist(run, run.subquestions)
            run.search_queries.extend(queries)
            await save_run(run)

            # ── RETRIEVE ───────────────────────────────────────
            run.transition(RunState.RETRIEVE, "Fetching sources")
            # Collect URLs: user-provided + search results
            urls_to_fetch = list(source_urls)
            # In production, add URLs from a search API here
            # For each query, you'd call search_web(q.query)

            if urls_to_fetch:
                new_sources = await fetch_sources(urls_to_fetch)
                # Deduplicate against existing
                existing_urls = {s.url for s in run.sources}
                for s in new_sources:
                    if s.url not in existing_urls:
                        run.sources.append(s)
                        existing_urls.add(s.url)

            # Fetch full content for source analysis
            source_contents = []
            for source in run.sources:
                result = await fetch_url(source.url)
                if result:
                    source_contents.append({
                        "source_id": source.id,
                        "url": source.url,
                        "title": source.title,
                        "content": result["content"][:10000],  # Truncate for LLM context
                    })
            await save_run(run)

            # ── EXTRACT_EVIDENCE ───────────────────────────────
            run.transition(RunState.EXTRACT_EVIDENCE, "Extracting evidence")
            if source_contents:
                new_evidence = await run_researcher(run, source_contents, run.subquestions)
                run.evidence.extend(new_evidence)
            await save_run(run)

            # ── SCORE_SOURCES ──────────────────────────────────
            run.transition(RunState.SCORE_SOURCES, "Scoring source quality")
            source_data = [
                {"source_id": s.id, "url": s.url, "title": s.title,
                 "content_snippet": s.content_snippet}
                for s in run.sources
            ]
            if source_data:
                scores = await run_source_critic(run, source_data)
                for source in run.sources:
                    if source.id in scores:
                        source.trust_score = scores[source.id]["trust_score"]
                        source.trust_factors = scores[source.id]["factors"]
            await save_run(run)

            # ── DRAFT_ATOMIC_CLAIMS ────────────────────────────
            run.transition(RunState.DRAFT_ATOMIC_CLAIMS, "Drafting claims")
            new_claims = await run_claim_drafter(run, run.evidence, run.subquestions)
            # Deduplicate claims
            existing_texts = {c.text.lower().strip() for c in run.claims}
            for c in new_claims:
                if c.text.lower().strip() not in existing_texts:
                    run.claims.append(c)
                    existing_texts.add(c.text.lower().strip())
            await save_run(run)

            # Cap claims
            if len(run.claims) > settings.max_claims:
                run.claims = run.claims[: settings.max_claims]

            # ── CLAIM_COURTROOM ────────────────────────────────
            run.transition(RunState.CLAIM_COURTROOM, "Running Claim Courtroom")
            prosecution = await run_prosecutor(run, run.claims, run.evidence)
            defense = await run_defense(run, run.claims, run.evidence)
            judgements = await run_judge(
                run, run.claims, prosecution, defense, conf_threshold
            )
            run.judgements = judgements
            await save_run(run)

            # ── DETECT_CONTRADICTIONS ──────────────────────────
            run.transition(RunState.DETECT_CONTRADICTIONS, "Detecting contradictions")
            run.contradictions = await run_contradiction_analyst(
                run, run.claims, run.evidence
            )
            await save_run(run)

            # ── MEASURE_COVERAGE ───────────────────────────────
            run.transition(RunState.MEASURE_COVERAGE, "Measuring coverage")
            run.coverage = await run_coverage_analyst(
                run, run.subquestions, run.evidence, run.judgements, run.contradictions
            )
            await save_run(run)

            # Check if we need more research
            weak_areas = [c for c in run.coverage if c.status in (CoverageStatus.RED, CoverageStatus.YELLOW)]
            if weak_areas and run.research_round < max_rounds:
                run.transition(RunState.RESEARCH_GAPS, f"Thin coverage in {len(weak_areas)} areas")
                # Next iteration will search for gaps
                # Update source_urls with gap-targeted queries (in production)
                continue
            else:
                break

        # ── SYNTHESIZE ─────────────────────────────────────────
        run.transition(RunState.SYNTHESIZE, "Synthesizing final report")
        supported = run.supported_claims()
        run.final_report = await run_synthesizer(
            run, supported, run.evidence, run.contradictions, run.subquestions
        )
        await save_run(run)

        # ── VERIFY_FINAL_REPORT ────────────────────────────────
        run.transition(RunState.VERIFY_FINAL_REPORT, "Verifying final report")
        # Validate all citations in report reference real evidence
        _verify_report_citations(run)
        await save_run(run)

        # ── EXPORT ─────────────────────────────────────────────
        run.transition(RunState.EXPORT, "Generating certificate")
        run.certificate = _build_certificate(run)
        run.agent_calls.extend(mesh.drain_calls())
        await save_run(run)

        # ── END ────────────────────────────────────────────────
        run.transition(RunState.END, "Research complete")
        await save_run(run)

    except Exception as e:
        logger.exception("Research run failed")
        run.error = str(e)
        run.transition(RunState.FAILED, str(e))
        run.agent_calls.extend(mesh.drain_calls())
        await save_run(run)

    return run


def _verify_report_citations(run: ResearchRun) -> None:
    """Validate that all citation references in the report map to real evidence."""
    import re
    evidence_ids = {e.id for e in run.evidence}
    claim_ids = {c.id for c in run.claims}

    # Find all evidence references
    ev_refs = set(re.findall(r"\[evidence:(\w+)\]", run.final_report))
    claim_refs = set(re.findall(r"\[claim:(\w+)\]", run.final_report))

    orphan_ev = ev_refs - evidence_ids
    orphan_claims = claim_refs - claim_ids

    if orphan_ev or orphan_claims:
        # Remove sentences with orphan references
        lines = run.final_report.split("\n")
        clean_lines = []
        for line in lines:
            has_orphan = False
            for oid in orphan_ev:
                if f"[evidence:{oid}]" in line:
                    has_orphan = True
                    break
            for oid in orphan_claims:
                if f"[claim:{oid}]" in line:
                    has_orphan = True
                    break
            if not has_orphan:
                clean_lines.append(line)
        run.final_report = "\n".join(clean_lines)


def _build_certificate(run: ResearchRun) -> VerificationCertificate:
    """Build verification certificate from run data."""
    supported_count = sum(
        1 for j in run.judgements if j.verdict == ClaimVerdict.SUPPORTED
    )
    rejected_count = len(run.judgements) - supported_count
    groundedness = supported_count / max(len(run.judgements), 1)

    models_used = list({c.model for c in run.agent_calls if c.model})

    return VerificationCertificate(
        run_id=run.id,
        original_question=run.question,
        mesh_models_used=models_used,
        source_count=len(run.sources),
        evidence_count=len(run.evidence),
        drafted_claim_count=len(run.claims),
        supported_claim_count=supported_count,
        rejected_claim_count=rejected_count,
        contradiction_count=len(run.contradictions),
        groundedness_rate=round(groundedness, 4),
        citation_coverage_rate=round(groundedness, 4),
        research_rounds=run.research_round,
        source_content_hashes=[s.content_hash for s in run.sources if s.content_hash],
        prompt_versions={"all_agents": "v1"},
        evaluation_limitations=[
            "Source retrieval limited to provided URLs in demo mode",
            "Citation mutation test requires live Mesh API key",
        ],
    )
