import pytest
from app.models.schemas import ResearchRun
from app.storage import database


@pytest.mark.asyncio
async def test_real_sqlite_roundtrip_and_readiness(tmp_path, monkeypatch):
    path = str(tmp_path / "persistent.db")
    monkeypatch.setattr(database, "DB_PATH", path)
    assert await database.database_ready() is False
    await database.init_db()
    run = ResearchRun(question="Persisted research settings", confidence_threshold=0.85, max_rounds=2)
    await database.save_run(run)
    loaded = await database.load_run(run.id)
    assert loaded.confidence_threshold == 0.85
    assert loaded.max_rounds == 2
    assert await database.database_ready() is True
    assert (await database.list_runs())[0]["id"] == run.id


@pytest.mark.asyncio
async def test_usage_persists_at_checkpoint_without_waiting_for_terminal_state(tmp_path, monkeypatch):
    from app.core.mesh_gateway import mesh
    from app.models.schemas import AgentCall, RunState
    from app.services.orchestrator import save_run

    monkeypatch.setattr(database, 'DB_PATH', str(tmp_path/'checkpoint.db'))
    await database.init_db()
    run = ResearchRun(question='Usage checkpoint fixture', current_state=RunState.SEARCH)
    mesh.drain_calls()
    mesh._record_call(AgentCall(agent='planner',prompt_tokens=10,completion_tokens=2,total_tokens=12))
    await save_run(run)
    await save_run(run)
    saved = await database.load_run(run.id)
    assert saved.current_state == RunState.SEARCH
    assert len(saved.agent_calls) == 1
    assert saved.agent_calls[0].total_tokens == 12


@pytest.mark.asyncio
async def test_cancelled_research_persists_failed_state_and_unknown_attempt(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from app.core.mesh_gateway import mesh
    from app.models.schemas import RunState
    from app.services.orchestrator import run_research

    class Completions:
        async def create(self, **kwargs):
            raise asyncio.CancelledError()

    monkeypatch.setattr(database, 'DB_PATH', str(tmp_path/'cancelled.db'))
    monkeypatch.setattr(mesh, '_client', SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
    await database.init_db()
    with pytest.raises(asyncio.CancelledError):
        await run_research('Cancellation persistence fixture', run_id='cancelled', max_rounds=1)
    saved = await database.load_run('cancelled')
    assert saved.current_state == RunState.FAILED
    assert 'incomplete' in saved.error
    assert len(saved.agent_calls) == 1
    assert saved.agent_calls[0].error == 'CancelledError'
    assert saved.agent_calls[0].total_tokens is None
