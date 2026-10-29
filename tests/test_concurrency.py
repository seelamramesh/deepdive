"""CHANGED: Deterministic concurrency tests; no model, search or external HTTP calls."""

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import ValidationError

from app.api import routes
from app.core.config import Settings
from app.models.schemas import ResearchRun
from app.services import orchestrator
from app.storage import database


# CHANGED: Shared isolated ASGI harness exercises real API admission and wrapper.
KEY = "offline-concurrency-" + "x" * 40
PAYLOAD = {"question": "Offline bounded research concurrency test"}


@pytest_asyncio.fixture
async def harness(monkeypatch):
    limiter = orchestrator.ResearchConcurrencyLimiter(3)
    monkeypatch.setattr(orchestrator, "concurrency_limiter", limiter)
    monkeypatch.setattr(routes.settings, "deepdive_api_key", KEY)
    monkeypatch.setattr(routes, "_running", {})
    save = AsyncMock()
    monkeypatch.setattr(database, "save_run", save)
    monkeypatch.setattr(routes, "load_run", AsyncMock(return_value=ResearchRun(question="Parent")))
    release = asyncio.Event()
    entered = asyncio.Queue()

    async def pipeline(*args, **kwargs):
        entered.put_nowait(args[0])
        await release.wait()
        return "finished"

    monkeypatch.setattr(orchestrator, "_run_research", pipeline)
    app = FastAPI()
    app.include_router(routes.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        try:
            yield client, limiter, release, entered, save
        finally:
            tasks = list(routes._running.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0)  # Flush idempotent completion callbacks.


# CHANGED: Event-driven synchronization, with a timeout only to detect hangs.
async def wait_for_entries(entered, count):
    for _ in range(count):
        await asyncio.wait_for(entered.get(), timeout=2)


# CHANGED: Four direct callers share the module-global three-slot limit.
@pytest.mark.asyncio
async def test_fourth_run_queues_when_max_three(harness):
    _, limiter, release, entered, _ = harness
    tasks = [asyncio.create_task(orchestrator.run_research(f"Question {i}")) for i in range(4)]
    try:
        await wait_for_entries(entered, 3)
        assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 3, "queued": 1}
        assert entered.empty()
        release.set()
        assert await asyncio.gather(*tasks) == ["finished"] * 4
        assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


# CHANGED: Both paid entry points reject before persistence and preserve auth order.
@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/research", "/runs/parent/follow-up"])
async def test_fourth_api_run_returns_429_and_auth_still_runs_first(harness, path):
    client, limiter, _, entered, save = harness
    limiter.reject_when_full = True
    for _ in range(3):
        assert (await client.post("/research", json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})).status_code == 200
    await wait_for_entries(entered, 3)
    response = await client.post(path, json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})
    assert response.status_code == 429
    assert response.json() == {
        "error": "server_busy",
        "message": "Maximum concurrent research runs reached. Try again later.",
        "max_concurrent": 3,
    }
    assert (await client.post(path, json=PAYLOAD)).status_code == 401
    assert save.await_count == 3
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 3, "queued": 0}


# CHANGED: Queue counts are visible through existing and requested health paths.
@pytest.mark.asyncio
async def test_concurrency_health_counts_queue_and_drains(harness):
    client, limiter, release, entered, _ = harness
    for _ in range(4):
        assert (await client.post("/research", json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})).status_code == 200
    await wait_for_entries(entered, 3)
    for path in ["/health/concurrency", "/api/health/concurrency"]:
        assert (await client.get(path)).json() == {"max_concurrent": 3, "active_runs": 3, "queued": 1}
    tasks = list(routes._running.values())
    release.set()
    await asyncio.gather(*tasks)
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}


# CHANGED: Errors outside the state machine still release the execution slot.
@pytest.mark.asyncio
async def test_semaphore_releases_on_orchestrator_exception(harness, monkeypatch):
    _, limiter, _, _, _ = harness
    monkeypatch.setattr(orchestrator, "_run_research", AsyncMock(side_effect=RuntimeError("offline failure")))
    with pytest.raises(RuntimeError, match="offline failure"):
        await orchestrator.run_research("Failure")
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}
    monkeypatch.setattr(orchestrator, "_run_research", AsyncMock(return_value="recovered"))
    assert await orchestrator.run_research("Next") == "recovered"


# CHANGED: Cancellation while queued and while active cannot leak reservations.
@pytest.mark.asyncio
async def test_cancellation_releases_active_and_queued_slots(harness):
    _, limiter, _, entered, _ = harness
    tasks = [asyncio.create_task(orchestrator.run_research(f"Cancel {i}")) for i in range(4)]
    try:
        await wait_for_entries(entered, 3)
        tasks[3].cancel()
        await asyncio.gather(tasks[3], return_exceptions=True)
        assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 3, "queued": 0}
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}


# CHANGED: Even cancellation before the background coroutine's first instruction releases.
@pytest.mark.asyncio
async def test_cancel_before_background_entry_releases_reservation(harness, monkeypatch):
    client, limiter, _, _, _ = harness
    real_track = routes._track_task

    def cancel_immediately(run_id, task):
        real_track(run_id, task)
        task.cancel()

    monkeypatch.setattr(routes, "_track_task", cancel_immediately)
    result = await client.post("/research", json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})
    assert result.status_code == 200
    await asyncio.gather(*list(routes._running.values()), return_exceptions=True)
    await asyncio.sleep(0)
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}


# CHANGED: Save failures return the reservation before any background work exists.
@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/research", "/runs/parent/follow-up"])
async def test_save_failure_releases_reservation(harness, path):
    client, limiter, _, _, save = harness
    save.side_effect = RuntimeError("offline database failure")
    with pytest.raises(RuntimeError, match="offline database failure"):
        await client.post(path, json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}
    assert routes._running == {}


# CHANGED: A burst cannot slip through before earlier tasks actually start.
def test_reject_reserves_slots_before_background_execution():
    limiter = orchestrator.ResearchConcurrencyLimiter(3, True)
    reservations = [limiter.reserve() for _ in range(3)]
    try:
        with pytest.raises(orchestrator.ConcurrencyLimitExceeded):
            limiter.reserve()
        assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 3}
    finally:
        for reservation in reservations:
            reservation.release()
            reservation.release()  # Cleanup is intentionally idempotent.
    assert limiter.queued == 0


# CHANGED: Environment-backed limits and booleans use existing settings validation.
@pytest.mark.parametrize("value", [0, 21])
def test_invalid_concurrency_configuration_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DEEPDIVE_MAX_CONCURRENT_RUNS=value)


def test_concurrency_settings_from_environment(monkeypatch):
    # CHANGED: No settings or credentials are printed or persisted.
    monkeypatch.setenv("DEEPDIVE_MAX_CONCURRENT_RUNS", "7")
    monkeypatch.setenv("DEEPDIVE_REJECT_WHEN_FULL", "true")
    configured = Settings(_env_file=None)
    assert configured.deepdive_max_concurrent_runs == 7
    assert configured.deepdive_reject_when_full is True


# CHANGED: Failed scheduling closes the unstarted coroutine and frees admission.
@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/research", "/runs/parent/follow-up"])
async def test_scheduling_failure_releases_reservation(harness, monkeypatch, path):
    client, limiter, _, _, _ = harness

    def cannot_schedule(coroutine):
        raise RuntimeError("offline scheduling failure")

    monkeypatch.setattr(routes.asyncio, "create_task", cannot_schedule)
    with pytest.raises(RuntimeError, match="offline scheduling failure"):
        await client.post(path, json=PAYLOAD, headers={"X-DeepDive-API-Key": KEY})
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}
    assert routes._running == {}


# CHANGED: A child task inherits context, but must still reserve its own slot.
@pytest.mark.asyncio
async def test_child_task_cannot_bypass_limiter_through_inherited_context(harness):
    _, limiter, release, entered, _ = harness
    async with limiter.reserve():
        task = asyncio.create_task(orchestrator.run_research("Child task"))
        try:
            await wait_for_entries(entered, 1)
            assert limiter.active_runs == 2
            release.set()
            assert await task == "finished"
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert limiter.snapshot() == {"max_concurrent": 3, "active_runs": 0, "queued": 0}


# CHANGED: Direct non-HTTP entry points honor the same rejection policy.
@pytest.mark.asyncio
async def test_direct_caller_rejected_when_capacity_reserved(harness):
    _, limiter, _, _, _ = harness
    limiter.reject_when_full = True
    reserved = [limiter.reserve() for _ in range(3)]
    try:
        with pytest.raises(orchestrator.ConcurrencyLimitExceeded) as error:
            await orchestrator.run_research("No capacity")
        assert error.value.max_concurrent == 3
    finally:
        for admission in reserved:
            admission.release()
