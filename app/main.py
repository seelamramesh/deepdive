"""DeepDive FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
import re
from markupsafe import Markup

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.services.security import render_report_markdown
from app.storage.database import init_db, list_runs, load_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="DeepDive — Self-Verifying Research Analyst",
    description="Multi-agent research system with claim verification",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

# Templates and static files
import os

_template_dir = os.path.join(os.path.dirname(__file__), "templates")
_static_dir = os.path.join(_template_dir, "static")

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

templates = Jinja2Templates(directory=_template_dir)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    runs = await list_runs()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"runs": runs})


@app.get("/run/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: str):
    run = await load_run(run_id)
    if not run:
        return HTMLResponse("<h1>Run not found</h1>", status_code=404)
    evidence_ids = set(re.findall(r"\[evidence:(\w+)\]", run.final_report))
    report_evidence = []
    for evidence in run.evidence:
        if evidence.id not in evidence_ids:
            continue
        source = run.get_source_by_id(evidence.source_id)
        report_evidence.append({"evidence": evidence, "source": source})
    return templates.TemplateResponse(
        request=request,
        name="run_detail.html",
        context={
            "run": run,
            "report_html": Markup(render_report_markdown(run.final_report)),
            "report_evidence": report_evidence,
        },
    )
