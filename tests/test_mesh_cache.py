import asyncio
from types import SimpleNamespace
import pytest
from app.core.mesh_gateway import MeshGateway


def gateway():
    g=MeshGateway();sent=[]
    class Completions:
        async def create(self,**kwargs):
            sent.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"verdicts":[{"claim_id":"c","verdict":"supported"}],"evidence":[{"id":"e"}]}'),finish_reason='stop')],usage=SimpleNamespace(prompt_tokens=10,completion_tokens=2,total_tokens=12))
    g._client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    return g,sent


@pytest.mark.asyncio
async def test_exact_cache_is_run_scoped_copies_output_and_does_not_double_count_tokens():
    g,sent=gateway();token=g.begin_cache_scope()
    first=await g.complete('judge','system','snapshot A',prompt_version='v1')
    first['verdicts'][0]['verdict']='changed'
    second=await g.complete('judge','system','snapshot A',prompt_version='v1')
    assert second['verdicts'][0]['verdict']=='supported' and len(sent)==1
    calls=g.drain_calls()
    assert calls[1].cache_hit and calls[1].request_sent is False
    assert calls[1].cache_source_call_id==calls[0].id
    assert calls[1].usage_source=='local_cache_incremental'
    assert sum(c.total_tokens for c in calls)==12
    g.end_cache_scope(token)
    await g.complete('judge','system','snapshot A',prompt_version='v1')
    assert len(sent)==2


@pytest.mark.asyncio
async def test_changed_evidence_version_model_and_settings_miss_cache():
    g,sent=gateway();token=g.begin_cache_scope()
    await g.complete('judge','system','A',model='model-a',prompt_version='v1')
    await g.complete('judge','system','B',model='model-a',prompt_version='v1')
    await g.complete('judge','system','A',model='model-a',prompt_version='v2')
    await g.complete('judge','system','A',model='model-b',prompt_version='v1')
    await g.complete('judge','system','A',model='model-a',prompt_version='v1',temperature=.2)
    assert len(sent)==5
    g.end_cache_scope(token)


@pytest.mark.asyncio
async def test_two_concurrent_runs_do_not_share_cached_answers():
    g,sent=gateway()
    async def run():
        token=g.begin_cache_scope()
        try:
            await g.complete('researcher','system','same')
            await asyncio.sleep(0)
            await g.complete('researcher','system','same')
        finally: g.end_cache_scope(token)
    await asyncio.gather(run(),run())
    assert len(sent)==2


@pytest.mark.asyncio
async def test_failed_json_is_not_cached(monkeypatch):
    g,sent=gateway();token=g.begin_cache_scope();count=0
    class Failing:
        async def create(self,**kwargs):
            nonlocal count
            count+=1
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='broken'),finish_reason='stop')])
    g._client=SimpleNamespace(chat=SimpleNamespace(completions=Failing()))
    monkeypatch.setattr('app.core.mesh_gateway.settings.mesh_json_attempts',1)
    for _ in range(2):
        with pytest.raises(ValueError): await g.complete('judge','system','A')
    assert count==2
    g.end_cache_scope(token)


@pytest.mark.asyncio
async def test_format_and_output_limit_changes_miss_cache(monkeypatch):
    g,sent=gateway();token=g.begin_cache_scope()
    await g.complete('judge','system','A')
    await g.complete('judge','system','A',response_format={'type':'json_object'})
    monkeypatch.setattr('app.core.mesh_gateway.settings.mesh_max_output_tokens',2048)
    await g.complete('judge','system','A')
    assert len(sent)==3
    g.end_cache_scope(token)


@pytest.mark.asyncio
async def test_provider_cache_metadata_is_not_assumed_when_missing():
    g,_=gateway()
    await g.complete('judge','system','A')
    assert g.drain_calls()[0].cached_prompt_tokens is None
    class Completions:
        async def create(self,**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"verdicts":[]}'),finish_reason='stop')],
                usage=SimpleNamespace(prompt_tokens=100,completion_tokens=10,total_tokens=110,prompt_tokens_details=SimpleNamespace(cached_tokens=80)))
    g._client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    await g.complete('judge','system','A')
    assert g.drain_calls()[0].cached_prompt_tokens==80


@pytest.mark.asyncio
async def test_local_cache_expires_after_five_minutes(monkeypatch):
    now=[0.0]
    monkeypatch.setattr('app.core.mesh_gateway.time.monotonic',lambda:now[0])
    g,sent=gateway();token=g.begin_cache_scope()
    await g.complete('judge','system','A')
    now[0]=301.0
    await g.complete('judge','system','A')
    assert len(sent)==2
    g.end_cache_scope(token)
