"""FastAPI routes for DeepDive API."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.config import settings
from app.core.mesh_gateway import mesh
from app.models.schemas import (
    ClaimVerdict,
    FollowUpRequest,
    HealthResponse,
    ResearchRequest,
    RunSummary,
)
from app.services.orchestrator import run_research
from app.storage.database import load_run, list_runs
from app.evaluation.benchmark import evaluate_run
from app.services.coverage import derive_coverage
from app.storage.database import database_ready

router = APIRouter()

# In-memory tracking of background tasks
_running: dict[str, asyncio.Task] = {}


def _track_task(run_id: str, task: asyncio.Task) -> None:
    _running[run_id] = task
    task.add_done_callback(lambda _: _running.pop(run_id, None))


@router.get("/health", response_model=HealthResponse)
async def health():
    db_ok = await database_ready()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        mesh_configured=mesh.is_configured,
        database=settings.database_path,
        db_ok=db_ok,
    )


@router.get("/runs")
async def get_runs():
    return await list_runs()


@router.get("/runs/{run_id}/workspace")
async def get_workspace(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    data = run.model_dump(mode="json")
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


@router.post("/research")
async def start_research(req: ResearchRequest, bg: BackgroundTasks):
    """Start a new research run (runs in background)."""
    from app.models.schemas import ResearchRun, RunState

    # Create placeholder run
    run = ResearchRun(question=req.question)
    # Return immediately with run ID
    from app.storage.database import save_run
    await save_run(run)

    async def _run():
        await run_research(
            question=req.question,
            source_urls=req.source_urls,
            max_rounds=req.max_rounds,
            confidence_threshold=req.confidence_threshold,
            run_id=run.id,
        )

    task = asyncio.create_task(_run())
    _track_task(run.id, task)

    return {"run_id": run.id, "status": "started", "question": req.question}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return RunSummary(
        id=run.id,
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
        "coverage": [c.model_dump() for c in run.coverage],
        "sources": [s.model_dump() for s in run.sources],
    }


@router.post("/runs/{run_id}/follow-up")
async def follow_up(run_id: str, req: FollowUpRequest, bg: BackgroundTasks):
    parent = await load_run(run_id)
    if not parent:
        raise HTTPException(404, "Parent run not found")

    # Reuse parent's sources
    source_urls = [s.url for s in parent.sources]

    from app.models.schemas import ResearchRun
    from app.storage.database import save_run

    child = ResearchRun(question=req.question)
    await save_run(child)

    async def _run():
        await run_research(
            question=req.question,
            source_urls=source_urls,
            max_rounds=req.max_rounds,
            confidence_threshold=req.confidence_threshold,
            run_id=child.id,
        )

    task = asyncio.create_task(_run())
    _track_task(child.id, task)

    return {"run_id": child.id, "parent_run_id": run_id, "status": "started"}


@router.get("/runs/{run_id}/evaluation")
async def get_run_evaluation(run_id: str):
    """Return deterministic quality metrics from persisted run artifacts."""
    run = await load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return evaluate_run(run)
