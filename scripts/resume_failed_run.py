"""Resume a failed run from its saved claims without repeating web search."""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.agents.runner import (
    run_contradiction_analyst,
    run_coverage_analyst,
    run_defense,
    run_judge,
    run_prosecutor,
    run_synthesizer,
)
from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.models.schemas import RunState
from app.services.orchestrator import (
    _build_certificate,
    _insufficient_evidence_report,
    _trusted_evidence,
    _verified_claim_report,
    _verify_report_citations,
)
from app.storage.database import load_run, save_run

logger = logging.getLogger(__name__)


async def resume(run_id: str) -> None:
    run = await load_run(run_id)
    if run is None:
        raise RuntimeError(f"Run not found: {run_id}")
    if not run.claims or not run.evidence:
        raise RuntimeError("Run has no saved claims or evidence to resume")

    run.error = None
    run.warnings = [
        warning for warning in run.warnings
        if not warning.startswith("Later research stage failed;")
    ]
    try:
        trusted_evidence = _trusted_evidence(run)
        if not trusted_evidence:
            raise RuntimeError("Run has no evidence from sources meeting trust threshold")
        run.transition(RunState.CLAIM_COURTROOM, "Resuming failed run from saved claims")
        prosecution = await run_prosecutor(run, run.claims, trusted_evidence)
        defense = await run_defense(run, run.claims, trusted_evidence)
        run.judgements = await run_judge(
            run, run.claims, prosecution, defense, settings.confidence_threshold
        )
        await save_run(run)

        run.transition(RunState.DETECT_CONTRADICTIONS, "Detecting contradictions")
        run.contradictions = await run_contradiction_analyst(run, run.claims, run.evidence)
        await save_run(run)

        run.transition(RunState.MEASURE_COVERAGE, "Measuring coverage")
        run.coverage = await run_coverage_analyst(
            run, run.subquestions, run.evidence, run.judgements, run.contradictions
        )
        await save_run(run)

        run.transition(RunState.SYNTHESIZE, "Synthesizing final report")
        supported = run.supported_claims(settings.confidence_threshold)
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

        run.transition(RunState.VERIFY_FINAL_REPORT, "Verifying final report")
        _verify_report_citations(run)
        run.transition(RunState.EXPORT, "Generating certificate")
        run.agent_calls.extend(mesh.drain_calls())
        run.certificate = _build_certificate(run)
        run.transition(RunState.END, "Research complete after recovery")
        await save_run(run)
        print(f"resumed {run.id}: {len(supported)} verified claims")
    except Exception as exc:
        logger.exception("Run recovery failed")
        run.error = str(exc)
        run.transition(RunState.FAILED, str(exc))
        run.agent_calls.extend(mesh.drain_calls())
        await save_run(run)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    arguments = parser.parse_args()
    asyncio.run(resume(arguments.run_id))
