"""Research orchestrator — drives the state machine end to end."""

from __future__ import annotations

import logging
import asyncio
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
    AtomicClaim,
    ClaimVerdict,
    CoverageEntry,
    CoverageStatus,
    ResearchRun,
    RunState,
    VerificationCertificate,
    _hash,
)
from app.services.retrieval import fetch_sources, search_web, select_extraction_window
from app.services.report_grounding import review_report
from app.storage.database import save_run as _persist_run

logger = logging.getLogger(__name__)


async def save_run(run: ResearchRun) -> None:
    """Persist observed call usage with each checkpoint, not only the final report."""
    run.agent_calls.extend(mesh.drain_calls())
    await _persist_run(run)


def _queries_for_round(queries: list, round_number: int, limit: int) -> list:
    """Select bounded queries while spreading coverage across subquestions."""
    if not queries or limit <= 0:
        return []
    first_by_subquestion = {}
    for query in queries:
        first_by_subquestion.setdefault(query.subquestion_id, query)
    diverse = list(first_by_subquestion.values())
    start = ((round_number - 1) * limit) % len(diverse)
    selected = [
        diverse[(start + offset) % len(diverse)]
        for offset in range(min(limit, len(diverse)))
    ]
    if len(selected) < limit:
        selected_ids = {query.id for query in selected}
        selected.extend(
            query for query in queries
            if query.id not in selected_ids
        )
    return selected[:limit]


def _select_claims_for_round(run: ResearchRun, new_claims: list[AtomicClaim], limit: int) -> list[AtomicClaim]:
    """Keep accepted claims and balance remaining slots across research areas."""
    candidates = [claim.model_copy(deep=True) for claim in run.claims]
    by_text = {" ".join(claim.text.casefold().split()): claim for claim in candidates}
    merged = {}
    fresh_ids = set()
    for claim in new_claims:
        key = " ".join(claim.text.casefold().split())
        if key in by_text:
            original = by_text[key]
            original.evidence_ids = list(dict.fromkeys(original.evidence_ids + claim.evidence_ids))
            merged[claim.id] = original.id
        else:
            candidate = claim.model_copy(deep=True)
            candidates.append(candidate)
            by_text[key] = candidate
            fresh_ids.add(candidate.id)
    accepted_ids = {claim.id for claim in run.supported_claims(run.confidence_threshold)}
    limit = max(0, limit)
    selected = [claim for claim in candidates if claim.id in accepted_ids][:limit]
    selected_ids = {claim.id for claim in selected}
    groups = {}
    for claim in candidates:
        if claim.id not in selected_ids:
            groups.setdefault(claim.subquestion_id, []).append(claim)
    for queue in groups.values():
        queue.sort(key=lambda claim: claim.id not in fresh_ids)
    counts = {group: sum(claim.subquestion_id == group for claim in selected) for group in groups}
    while len(selected) < limit and any(groups.values()):
        group = min((key for key, queue in groups.items() if queue), key=lambda key: counts[key])
        claim = groups[group].pop(0)
        selected.append(claim)
        selected_ids.add(claim.id)
        counts[group] += 1
    judgements = {item.claim_id: item for item in run.judgements}
    run.claim_selection_audit.append({
        "round": run.research_round, "limit": limit,
        "policy": "retain_accepted_then_balance_subquestions",
        "selected_claim_ids": [claim.id for claim in selected],
        "merged_duplicate_ids": merged,
        "excluded_from_active_budget": [
            {"claim": claim.model_dump(), "reason": "active_claim_budget",
             "previous_judgement": judgements[claim.id].model_dump(mode="json") if claim.id in judgements else None}
            for claim in candidates if claim.id not in selected_ids
        ],
    })
    return selected


def _insufficient_evidence_report(run: ResearchRun) -> str:
    """Return an honest terminal report when no claims passed verification."""
    return (
        f"# {run.question}: Research Report\n\n"
        "## Outcome\n\n"
        "**Insufficient verified evidence to produce a factual report.**\n\n"
        "DeepDive found no claims that passed source-grounding and verification checks. "
        "Rather than fill sections with unsupported text, this run withheld conclusions.\n\n"
        "## Run Diagnostics\n\n"
        f"- Research rounds: {run.research_round}\n"
        f"- Sources successfully retrieved: {len(run.sources)}\n"
        f"- Exact source passages accepted as evidence: {len(run.evidence)}\n"
        f"- Atomic claims drafted: {len(run.claims)}\n"
        f"- Claims passing verification: {len(run.supported_claims(run.confidence_threshold))}\n\n"
        "## Recommended Next Step\n\n"
        "Run again with additional authoritative source URLs, or broaden retrieval coverage. "
        "No market forecast should be inferred from this incomplete run.\n"
    )


def _trusted_evidence(run: ResearchRun) -> list:
    trusted_source_ids = {
        source.id for source in run.sources
        if source.trust_score >= settings.min_source_trust
    }
    return [
        evidence for evidence in run.evidence
        if evidence.source_id in trusted_source_ids
    ]


def _verified_claim_report(run: ResearchRun, supported_claims: list, reason: str = "Synthesizer output was unavailable.") -> str:
    """Build a deterministic report from validated claim/evidence links."""
    evidence_ids = {evidence.id for evidence in run.evidence}
    judgement_by_claim = {judgement.claim_id: judgement for judgement in run.judgements}
    verified_lines = []
    for claim in supported_claims:
        judgement = judgement_by_claim.get(claim.id)
        if not judgement:
            continue
        valid_ids = [
            evidence_id for evidence_id in judgement.supporting_evidence_ids
            if evidence_id in claim.evidence_ids and evidence_id in evidence_ids
        ]
        if valid_ids:
            verified_lines.append(
                f"- {claim.text} [claim:{claim.id}] [evidence:{valid_ids[0]}]"
            )
    if not verified_lines:
        return _insufficient_evidence_report(run)
    return (
        f"# {run.question}: Verified Research Report\n\n"
        "## Verified Findings\n\n"
        + "\n".join(verified_lines)
        + "\n\n## Limitations\n\n"
        f"{reason} Only claims with validated "
        "claim-to-evidence links are shown."
    )


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
    run.confidence_threshold = conf_threshold
    run.max_rounds = max_rounds
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
            selected_queries = _queries_for_round(
                queries, run.research_round, settings.max_search_queries_per_round
            )
            run.search_queries.extend(selected_queries)
            if run.search_audit:
                run.search_audit[-1]["selected_query_ids"] = [query.id for query in selected_queries]
            await save_run(run)

            # ── RETRIEVE ───────────────────────────────────────
            run.transition(RunState.RETRIEVE, "Fetching sources")
            # Collect URLs: user-provided + search results
            urls_to_fetch = list(source_urls)
            retrieval_event = {"round": run.research_round, "seed_urls": list(source_urls), "searches": []}
            run.retrieval_audit.append(retrieval_event)
            for query in selected_queries:
                result_urls = await search_web(query.query)
                retrieval_event["searches"].append({
                    "query_id": query.id, "query": query.query,
                    "result_urls": result_urls,
                    "outcome": "urls_returned" if result_urls else "no_urls_or_search_unavailable",
                })
                urls_to_fetch.extend(result_urls)
            candidate_urls = list(dict.fromkeys(urls_to_fetch))
            existing_urls = {source.url for source in run.sources}
            urls_to_fetch = [url for url in candidate_urls if url not in existing_urls][: settings.max_sources_per_round]
            retrieval_event["candidate_urls"] = candidate_urls
            retrieval_event["selected_urls"] = list(urls_to_fetch)
            retrieval_event["reused_source_ids"] = [source.id for source in run.sources]
            retrieval_event["fetched_sources"] = []

            if urls_to_fetch:
                new_sources = await fetch_sources(urls_to_fetch)
                retrieval_event["fetched_sources"] = [
                    {"source_id": source.id, "url": source.url, "content_hash": source.content_hash}
                    for source in new_sources
                ]
                # Deduplicate against existing
                existing_urls = {s.url for s in run.sources}
                for s in new_sources:
                    if s.url not in existing_urls:
                        run.sources.append(s)
                        existing_urls.add(s.url)

            # Source identity, metadata and extraction share one immutable snapshot.
            source_contents = []
            retrieval_event["extraction_inputs"] = []
            for source in run.sources:
                snapshot = source.content_snapshot
                if snapshot is not None and _hash(snapshot) == source.content_hash:
                    extraction_text, extraction_start, extraction_end = select_extraction_window(
                        snapshot, run.question
                    )
                    retrieval_event["extraction_inputs"].append({
                        "source_id": source.id, "url": source.url,
                        "characters_sent": len(extraction_text),
                        "analyzed_content_hash": _hash(extraction_text),
                        "source_record_hash": source.content_hash,
                        "snapshot_hash": _hash(snapshot),
                        "snapshot_start": extraction_start, "snapshot_end": extraction_end,
                        "selection_policy": "query_lexical_window_v1",
                        "snapshot_characters": len(snapshot),
                    })
                    source_contents.append({
                        "source_id": source.id,
                        "url": source.url,
                        "title": source.title,
                        "content": extraction_text,
                        "snapshot_hash": source.content_hash,
                    })
                else:
                    warning = f"Source {source.id} snapshot missing or hash mismatch; extraction withheld."
                    if warning not in run.warnings:
                        run.warnings.append(warning)
            await save_run(run)

            # ── EXTRACT_EVIDENCE ───────────────────────────────
            run.transition(RunState.EXTRACT_EVIDENCE, "Extracting evidence")
            if source_contents:
                new_evidence = await run_researcher(run, source_contents, run.subquestions)
                existing_hashes = {(e.source_id, e.passage_hash) for e in run.evidence}
                for evidence in new_evidence:
                    key = (evidence.source_id, evidence.passage_hash)
                    if key not in existing_hashes:
                        run.evidence.append(evidence)
                        existing_hashes.add(key)
            await save_run(run)

            # ── SCORE_SOURCES ──────────────────────────────────
            run.transition(RunState.SCORE_SOURCES, "Scoring source quality")
            selected_by_id = {item["source_id"]: item for item in source_contents}
            audit_by_id = {item["source_id"]: item for item in retrieval_event["extraction_inputs"]}
            source_data = [
                {"source_id": s.id, "url": s.url, "title": s.title,
                 "content_snippet": s.content_snippet,
                 "selected_content": selected_by_id[s.id]["content"],
                 "content_scope": "partial_snapshot_window",
                 "snapshot_hash": s.content_hash,
                 "snapshot_start": audit_by_id[s.id]["snapshot_start"],
                 "snapshot_end": audit_by_id[s.id]["snapshot_end"],
                 "snapshot_characters": audit_by_id[s.id]["snapshot_characters"]}
                for s in run.sources if s.id in selected_by_id
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
            trusted_evidence = _trusted_evidence(run)
            new_claims = (
                await run_claim_drafter(run, trusted_evidence, run.subquestions)
                if trusted_evidence else []
            )
            run.claims = _select_claims_for_round(run, new_claims, settings.max_claims)
            await save_run(run)

            # ── CLAIM_COURTROOM ────────────────────────────────
            run.transition(RunState.CLAIM_COURTROOM, "Running Claim Courtroom")
            if run.claims:
                prosecution = await run_prosecutor(run, run.claims, trusted_evidence)
                defense = await run_defense(run, run.claims, trusted_evidence)
                run.prosecution = prosecution
                run.defense = defense
                run.judgements = await run_judge(
                    run, run.claims, prosecution, defense, conf_threshold, trusted_evidence
                )
            else:
                run.judgements = []
            await save_run(run)

            # ── DETECT_CONTRADICTIONS ──────────────────────────
            run.transition(RunState.DETECT_CONTRADICTIONS, "Detecting contradictions")
            run.contradictions = (
                await run_contradiction_analyst(run, run.claims, run.evidence)
                if run.claims else []
            )
            await save_run(run)

            # ── MEASURE_COVERAGE ───────────────────────────────
            run.transition(RunState.MEASURE_COVERAGE, "Measuring coverage")
            if run.evidence:
                run.coverage = await run_coverage_analyst(
                    run, run.subquestions, run.evidence, run.judgements, run.contradictions
                )
            else:
                run.coverage = [
                    CoverageEntry(subquestion_id=s.id, subquestion_text=s.text)
                    for s in run.subquestions
                ]
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
        supported = run.supported_claims(conf_threshold)
        if supported:
            try:
                run.final_report = await run_synthesizer(
                    run, supported, run.evidence, run.contradictions, run.subquestions
                )
            except Exception as synthesis_error:
                warning = (
                    "Synthesizer returned malformed structured output; "
                    "deterministic verified-claim report used"
                )
                logger.warning("%s: %s", warning, synthesis_error)
                run.warnings.append(warning)
                run.final_report = _verified_claim_report(run, supported)
        else:
            run.final_report = _insufficient_evidence_report(run)
        await save_run(run)

        # ── VERIFY_FINAL_REPORT ────────────────────────────────
        run.transition(RunState.VERIFY_FINAL_REPORT, "Verifying final report")
        # Review prose before structural citation checks; missing decisions withhold units.
        if supported:
            await review_report(run)
        _verify_report_citations(run)
        await save_run(run)

        # ── EXPORT ─────────────────────────────────────────────
        run.transition(RunState.EXPORT, "Generating certificate")
        run.agent_calls.extend(mesh.drain_calls())
        run.certificate = _build_certificate(run)
        await save_run(run)

        # ── END ────────────────────────────────────────────────
        run.transition(RunState.END, "Research complete")
        await save_run(run)

    except asyncio.CancelledError:
        run.error = "Research execution cancelled; final usage may be incomplete."
        run.transition(RunState.FAILED, "Research task cancelled")
        await save_run(run)
        raise
    except Exception as e:
        logger.exception("Research run failed")
        supported = run.supported_claims(conf_threshold)
        if supported:
            try:
                warning = f"Later research stage failed; report uses last verified checkpoint: {e}"
                run.warnings.append(warning)
                run.error = None
                run.transition(RunState.SYNTHESIZE, "Recovering from last verified checkpoint")
                run.final_report = await run_synthesizer(
                    run, supported, run.evidence, run.contradictions, run.subquestions
                )
                await review_report(run)
                _verify_report_citations(run)
                run.agent_calls.extend(mesh.drain_calls())
                run.certificate = _build_certificate(run)
                run.certificate.evaluation_limitations.append(warning)
                run.transition(RunState.END, "Research complete with partial-results warning")
                await save_run(run)
                return run
            except Exception as recovery_error:
                logger.exception("Partial-result recovery failed")
                e = recovery_error
        run.error = str(e)
        run.transition(RunState.FAILED, str(e))
        run.agent_calls.extend(mesh.drain_calls())
        await save_run(run)

    return run


def _verify_report_citations(run: ResearchRun) -> None:
    """Validate that all citation references in the report map to real evidence."""
    import re
    evidence_ids = {e.id for e in run.evidence}
    supported_claims = run.supported_claims(run.confidence_threshold)
    claim_ids = {c.id for c in supported_claims}
    supported_claim_by_id = {claim.id: claim for claim in supported_claims}
    allowed_links = {
        (judgement.claim_id, evidence_id)
        for judgement in run.judgements
        if judgement.claim_id in supported_claim_by_id
        and judgement.verdict == ClaimVerdict.SUPPORTED
        and judgement.confidence >= run.confidence_threshold
        for evidence_id in judgement.supporting_evidence_ids
        if evidence_id in supported_claim_by_id[judgement.claim_id].evidence_ids
        and evidence_id in evidence_ids
    }

    # Find all evidence references
    ev_refs = set(re.findall(r"\[evidence:(\w+)\]", run.final_report))
    claim_refs = set(re.findall(r"\[claim:(\w+)\]", run.final_report))

    allowed_evidence_ids = {evidence_id for _, evidence_id in allowed_links}
    orphan_ev = (ev_refs - evidence_ids) | (ev_refs - allowed_evidence_ids)
    orphan_claims = claim_refs - claim_ids

    lines = run.final_report.split("\n")
    clean_lines = []
    for line in lines:
        has_orphan = any(f"[evidence:{oid}]" in line for oid in orphan_ev)
        has_orphan = has_orphan or any(f"[claim:{oid}]" in line for oid in orphan_claims)
        line_claims = re.findall(r"\[claim:(\w+)\]", line)
        line_evidence = re.findall(r"\[evidence:(\w+)\]", line)
        has_unapproved_link = bool(line_claims and line_evidence) and (
            any(not any((claim_id, evidence_id) in allowed_links
                        for evidence_id in line_evidence) for claim_id in line_claims)
            or any(not any((claim_id, evidence_id) in allowed_links
                           for claim_id in line_claims) for evidence_id in line_evidence)
        )
        stripped = line.strip()
        is_heading = not stripped or stripped.startswith("#")
        has_required_citations = bool(
            re.search(r"\[claim:\w+\]", line)
            and re.search(r"\[evidence:\w+\]", line)
        )
        if not has_orphan and not has_unapproved_link and (is_heading or has_required_citations):
            clean_lines.append(line)
    compact_lines = []
    for index, line in enumerate(clean_lines):
        stripped = line.strip()
        heading = re.match(r"^(#{2,6})\s+", stripped)
        if heading:
            current_level = len(heading.group(1))
            next_content = ""
            for candidate in clean_lines[index + 1:]:
                if candidate.strip():
                    next_content = candidate.strip()
                    break
            next_heading = re.match(r"^(#{1,6})\s+", next_content)
            if not next_content or (next_heading and len(next_heading.group(1)) <= current_level):
                continue
        compact_lines.append(line)
    run.final_report = "\n".join(compact_lines)
    if not re.search(r"\[claim:\w+\].*\[evidence:\w+\]", run.final_report):
        reason = "Generated prose did not survive report review or citation validation."
        run.report_fallback_reason = reason
        run.report_grounding_status = "accepted_claim_fallback"
        warning = reason + " Deterministic accepted-claim fallback shown; this is not a fully reviewed synthesis."
        if warning not in run.warnings:
            run.warnings.append(warning)
        run.final_report = _verified_claim_report(run, supported_claims, reason)
    final_lines = set(run.final_report.splitlines())
    for decision in run.report_grounding_audit:
        decision["included_in_final_report"] = bool(decision.get("kept") is True and decision.get("text") in final_lines)


def _build_certificate(run: ResearchRun) -> VerificationCertificate:
    """Build verification certificate from run data."""
    supported = run.supported_claims(run.confidence_threshold)
    supported_ids = {claim.id for claim in supported}
    supported_count = len(supported)
    rejected_count = len(run.claims) - supported_count
    groundedness = supported_count / max(len(run.claims), 1)
    evidence_ids = {evidence.id for evidence in run.evidence}
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
    citation_coverage = valid_citation_links / max(len(citation_links), 1)

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
        citation_coverage_rate=round(citation_coverage, 4),
        research_rounds=run.research_round,
        source_content_hashes=[s.content_hash for s in run.sources if s.content_hash],
        prompt_versions={call.agent: call.prompt_version for call in run.agent_calls},
        evaluation_limitations=[
            "Search coverage depends on Brave Search results and retrievable public pages",
            "Certificate metrics measure internal claim-to-evidence integrity, not external truth",
            "Model report review is not a hallucination-free guarantee or independent human verification",
            f"Report review status: {run.report_grounding_status}; accepted-claim fallback may be used when generated prose is withheld",
            "Audit kept decisions describe model review; included_in_final_report records subsequent citation filtering",
            "Claim counts and verification rates refer to active claims; budget exclusions and prior decisions are recorded separately in claim_selection_audit",
        ],
    )
