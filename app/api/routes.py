"""FastAPI routes for DeepDive API."""

from __future__ import annotations

import asyncio
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
# CHANGED: Exact top-level 429 response, without HTTPException's detail wrapper.
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.model_presets import AGENT_TIER_MAP, preset_catalog, resolve_model
from app.core.mesh_gateway import mesh
from app.models.schemas import (
    ClaimVerdict,
    FollowUpRequest,
    HealthResponse,
    ResearchRequest,
    RunSummary,
)
from app.services.orchestrator import run_research
# CHANGED: Resolve the shared limiter at call time, including follow-up requests.
from app.services import orchestrator
from app.storage.database import load_run, list_runs
from app.evaluation.benchmark import evaluate_run
from app.services.coverage import derive_coverage
from app.storage.database import database_ready

router = APIRouter()

async def require_research_key(x_deepdive_api_key: str | None = Header(default=None)) -> None:
    """Fail closed before saving a run or scheduling any paid work."""
    expected = settings.deepdive_api_key
    if len(expected.encode("utf-8")) < 32:
        raise HTTPException(503, "Research is locked. Owner must configure an access key.")
    supplied = (x_deepdive_api_key or "").encode("utf-8")
    if not secrets.compare_digest(supplied, expected.encode("utf-8")):
        raise HTTPException(401, "Research access key required or invalid.")


# In-memory tracking of background tasks
_running: dict[str, asyncio.Task] = {}


def _track_task(run_id: str, task: asyncio.Task) -> None:
    _running[run_id] = task
    task.add_done_callback(lambda _: _running.pop(run_id, None))


# CHANGED: Authentication dependencies finish before endpoint admission checks.
def _reserve_research() -> orchestrator.RunAdmission | JSONResponse:
    try:
        return orchestrator.concurrency_limiter.reserve()
    except orchestrator.ConcurrencyLimitExceeded as exc:
        return JSONResponse(status_code=429, content={
            "error": "server_busy", "message": str(exc),
            "max_concurrent": exc.max_concurrent,
        })


# CHANGED: Preserve unprefixed API conventions and expose the requested alias.
@router.get("/health/concurrency")
@router.get("/api/health/concurrency")
async def health_concurrency():
    return orchestrator.concurrency_limiter.snapshot()


@router.get("/health", response_model=HealthResponse)
async def health():
    db_ok = await database_ready()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        mesh_configured=mesh.is_configured,
        database=settings.database_path,
        db_ok=db_ok,
    )


@router.get("/model-presets")
async def get_model_presets():
    return preset_catalog()


@router.get("/runs")
async def get_runs():
    return await list_runs()


@router.get("/runs/{run_id}/workspace")
async def get_workspace(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    from app.services.provenance import material_groups
    data = run.model_dump(mode="json")
    data["source_material_groups"] = material_groups(run.sources)
    data["source_independence_note"] = "Shared publication identifiers, matching snapshots or probable identical journal/preprint titles are grouped. Title matches are heuristic; distinct groups do not prove independence."
    data["warnings"] = [
        "Partial recovery: a later research agent returned malformed output. This report uses the last verified checkpoint; findings remain partial."
        if warning.startswith("Later research stage failed; report uses last verified checkpoint")
        else warning
        for warning in run.warnings
    ]
    data["accepted_claim_ids"] = [claim.id for claim in run.supported_claims(run.confidence_threshold)]
    data["recorded_coverage"] = data["coverage"]
    data["coverage"] = [entry.model_dump(mode="json") for entry in derive_coverage(run, data["recorded_coverage"])]
    data["coverage_derivation"] = "Counts derived from saved artifacts; assessment labels remain heuristic and evidence-gated."

    # Retain snapshots in storage without inflating the public workspace response.
    data["sources"] = [
        {key: value for key, value in source.items() if key != "content_snapshot"}
        for source in data["sources"]
    ]
    data["agent_calls"] = [
        {key: value for key, value in call.model_dump(mode="json").items()
         if key not in {"response_preview", "error"}}
        for call in run.agent_calls
    ]
    return data


@router.post("/research", dependencies=[Depends(require_research_key)])
async def start_research(req: ResearchRequest, bg: BackgroundTasks):
    """Start a new research run (runs in background)."""
    from app.models.schemas import ResearchRun, RunState

    # Create placeholder run
    run = ResearchRun(question=req.question, model_preset=req.model_preset, resolved_models={a:resolve_model(req.model_preset,a) for a in AGENT_TIER_MAP})
    # Return immediately with run ID
    from app.storage.database import save_run
    # CHANGED: Reserve before saving; rejected requests create no placeholder.
    admission = _reserve_research()
    if isinstance(admission, JSONResponse):
        return admission
    try:
        await save_run(run)
    except BaseException:
        admission.release()
        raise

    async def _run():
        # CHANGED: Hold the reserved slot while preserving run_research's public arguments.
        async with admission:
            await run_research(
                question=req.question,
                source_urls=req.source_urls,
                max_rounds=req.max_rounds,
                confidence_threshold=req.confidence_threshold,
                model_preset=req.model_preset,
                run_id=run.id,
            )

    # CHANGED: Release even when scheduling fails or cancellation precedes entry.
    pending = _run()
    try:
        task = asyncio.create_task(pending)
    except BaseException:
        pending.close()
        admission.release()
        raise
    task.add_done_callback(lambda _: admission.release())
    _track_task(run.id, task)

    return {"run_id": run.id, "status": "started", "question": req.question}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return RunSummary(
        id=run.id,
        model_preset=run.model_preset,
        question=run.question,
        state=run.current_state,
        created_at=run.created_at,
        source_count=len(run.sources),
        claim_count=len(run.claims),
        supported_claim_count=len(run.supported_claims(run.confidence_threshold)),
        contradiction_count=len(run.contradictions),
        research_rounds=run.research_round,
        error=run.error,
    )


@router.get("/runs/{run_id}/audit")
async def get_audit(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return {
        "run_id": run.id,
        "state_transitions": [t.model_dump() for t in run.state_transitions],
        "agent_calls": [c.model_dump() for c in run.agent_calls],
        "subquestions": [s.model_dump() for s in run.subquestions],
        "search_queries": [q.model_dump() for q in run.search_queries],
    }


@router.get("/runs/{run_id}/claims")
async def get_claims(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    supported = run.supported_claims(run.confidence_threshold)
    supported_ids = {claim.id for claim in supported}
    return {
        "claims": [c.model_dump() for c in run.claims],
        "judgements": [j.model_dump() for j in run.judgements],
        "supported": [c.model_dump() for c in supported],
        "rejected": [
            c.model_dump() for c in run.claims
            if c.id not in supported_ids
        ],
    }


@router.get("/runs/{run_id}/contradictions")
async def get_contradictions(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return {"contradictions": [c.model_dump() for c in run.contradictions]}


@router.get("/runs/{run_id}/certificate")
async def get_certificate(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if not run.certificate:
        raise HTTPException(400, "Run not complete — no certificate yet")
    return run.certificate.model_dump()


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return {
        "report": run.final_report,
        "verification_disclaimer": run.verification_disclaimer,
        "report_review_status": run.report_grounding_status,
        "model_preset": run.model_preset,
        "coverage": [c.model_dump() for c in run.coverage],
        "sources": [s.model_dump() for s in run.sources],
    }


@router.post("/runs/{run_id}/follow-up", dependencies=[Depends(require_research_key)])
async def follow_up(run_id: str, req: FollowUpRequest, bg: BackgroundTasks):
    parent = await load_run(run_id)
    if not parent:
        raise HTTPException(404, "Parent run not found")

    # Reuse parent's sources
    source_urls = [s.url for s in parent.sources]

    from app.models.schemas import ResearchRun
    from app.storage.database import save_run

    child = ResearchRun(question=req.question, model_preset=req.model_preset, resolved_models={a:resolve_model(req.model_preset,a) for a in AGENT_TIER_MAP})
    # CHANGED: Follow-ups share the same process-wide admission budget.
    admission = _reserve_research()
    if isinstance(admission, JSONResponse):
        return admission
    try:
        await save_run(child)
    except BaseException:
        admission.release()
        raise

    async def _run():
        # CHANGED: Hold the reserved slot while preserving run_research's public arguments.
        async with admission:
            await run_research(
                question=req.question,
                source_urls=source_urls,
                max_rounds=req.max_rounds,
                confidence_threshold=req.confidence_threshold,
                model_preset=req.model_preset,
                run_id=child.id,
            )

    # CHANGED: Match initial research cleanup on scheduling/cancellation failure.
    pending = _run()
    try:
        task = asyncio.create_task(pending)
    except BaseException:
        pending.close()
        admission.release()
        raise
    task.add_done_callback(lambda _: admission.release())
    _track_task(child.id, task)

    return {"run_id": child.id, "parent_run_id": run_id, "status": "started"}


@router.get("/runs/{run_id}/evaluation")
async def get_run_evaluation(run_id: str):
    """Return deterministic quality metrics from persisted run artifacts."""
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return evaluate_run(run)
