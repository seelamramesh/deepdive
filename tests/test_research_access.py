"""Authorization checks use ASGI and mocks only; never paid providers."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from app.api import routes
from app.storage import database

KEY = "offline-only-" + "x" * 40
PAYLOAD = {"question": "A valid but never dispatched research question"}


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/research", "/runs/parent/follow-up"])
@pytest.mark.parametrize("configured,supplied,status", [("", None, 503), ("short", "short", 503), (KEY, None, 401), (KEY, "wrong", 401), (KEY, "non-ascii-\u00e9", 401)])
async def test_unauthorized_requests_never_save_or_schedule(monkeypatch, path, configured, supplied, status):
    monkeypatch.setattr(routes.settings, "deepdive_api_key", configured)
    save = AsyncMock(); research = AsyncMock(); load = AsyncMock()
    monkeypatch.setattr(database, "save_run", save)
    monkeypatch.setattr(routes, "run_research", research)
    monkeypatch.setattr(routes, "load_run", load)
    app = FastAPI(); app.include_router(routes.router)
    headers = {} if supplied is None else {"X-DeepDive-API-Key": supplied}
    # Unicode injection tested directly below; HTTPX correctly enforces ASCII headers.
    if supplied and not supplied.isascii():
        with pytest.raises(Exception) as error:
            await routes.require_research_key(supplied)
        assert error.value.status_code == status
    else:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(path, json=PAYLOAD, headers=headers)
        assert response.status_code == status
        assert KEY not in response.text
    save.assert_not_called(); research.assert_not_called(); load.assert_not_called()


@pytest.mark.asyncio
async def test_owner_header_allows_mocked_research_and_readonly_remains_public(monkeypatch):
    monkeypatch.setattr(routes.settings, "deepdive_api_key", KEY)
    save = AsyncMock(); research = AsyncMock()
    monkeypatch.setattr(database, "save_run", save)
    monkeypatch.setattr(routes, "run_research", research)
    monkeypatch.setattr(routes, "list_runs", AsyncMock(return_value=[]))
    app = FastAPI(); app.include_router(routes.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/runs")).status_code == 200
        # Body and query-string keys are never accepted as authentication.
        assert (await client.post("/research", params={"api_key": KEY}, json=PAYLOAD | {"api_key": KEY})).status_code == 401
        result = await client.post("/research", json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})
        await asyncio.sleep(0)
    assert result.status_code == 200
    save.assert_awaited_once(); research.assert_awaited_once()
    assert KEY not in json.dumps(research.call_args.kwargs)
    assert KEY not in save.call_args.args[0].model_dump_json()


def test_workflow_forwards_caller_key_and_never_embeds_service_key():
    workflow = json.loads(Path("n8n/deepdive-research.json").read_text())
    assert len(workflow["nodes"]) == 14
    node = next(n for n in workflow["nodes"] if n["name"] == "Start Research Run")
    header, = node["parameters"]["headerParameters"]["parameters"]
    assert node["parameters"]["sendHeaders"] is True
    assert header["name"] == "X-DeepDive-API-Key"
    assert "$('Webhook').first().json.headers['x-deepdive-api-key']" in header["value"]
    assert "$env" not in header["value"]
