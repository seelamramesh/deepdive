"""All inference is mocked; catalog checks use the saved metadata snapshot."""
import asyncio
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from app.api import routes
from app.core.config import settings
from app.core.mesh_gateway import MeshGateway
from app.core.model_presets import AGENT_TIER_MAP, MODEL_PRESETS, CATALOG, resolve_model
from app.models.schemas import ResearchRequest, ResearchRun, VerificationCertificate, VERIFICATION_DISCLAIMER
from app.storage import database


@pytest.mark.parametrize('preset', list(MODEL_PRESETS))
@pytest.mark.parametrize('agent', list(AGENT_TIER_MAP))
def test_every_real_role_resolves_to_policy(preset, agent):
    tier=AGENT_TIER_MAP[agent]
    expected=settings.mesh_model if preset=='configured' else MODEL_PRESETS[preset]['models'][tier]
    assert resolve_model(preset,agent)==expected
    assert resolve_model(preset,agent,'explicit-model')=='explicit-model'
    if preset!='configured':assert expected in {m['id'] for m in CATALOG['models']}


def test_legacy_and_unknown_role_fallback_and_invalid_preset():
    assert len(AGENT_TIER_MAP)==12 and 'coordinator' not in AGENT_TIER_MAP
    assert AGENT_TIER_MAP['report_verifier']=='heavy'
    assert resolve_model(None,'judge')==settings.mesh_model
    assert resolve_model('configured',None)==settings.mesh_model
    assert resolve_model('balanced',None)=='openai/gpt-4o-mini'
    assert resolve_model('balanced','unknown')=='openai/gpt-4o-mini'
    assert ResearchRequest(question='Valid research question').model_preset=='balanced'
    with pytest.raises(ValidationError):ResearchRequest(question='Valid research question',model_preset='imaginary')
    with pytest.raises(ValueError):resolve_model('imaginary','judge')


@pytest.mark.asyncio
async def test_context_isolation_model_telemetry_and_cache_key():
    dispatched=[]
    class Completions:
        async def create(self,**kwargs):
            await asyncio.sleep(0);dispatched.append(kwargs['model'])
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"verdicts":[{"claim_id":"fixture"}]}'),finish_reason='stop')],usage=None)
    gateway=MeshGateway();gateway._client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    async def job(preset):
        token=gateway.begin_model_scope(preset);cache=gateway.begin_cache_scope()
        try:
            await gateway.complete('judge','system','same')
            await gateway.complete('judge','system','same')
            await gateway.complete('judge','system','same',model='explicit-other')
            return gateway.drain_calls()
        finally:gateway.end_cache_scope(cache);gateway.end_model_scope(token)
    fast,balanced=await asyncio.gather(job('fast'),job('balanced'))
    assert [c.model for c in fast]==['openai/gpt-4o-mini','openai/gpt-4o-mini','explicit-other']
    assert [c.model for c in balanced]==['openai/gpt-4o','openai/gpt-4o','explicit-other']
    assert fast[1].cache_hit and balanced[1].cache_hit and len(dispatched)==4
    assert gateway._preset.get() is None
    token=gateway.begin_model_scope('balanced')
    try:
        await gateway.complete(system_prompt='system',user_prompt='no role')
        assert gateway.drain_calls()[0].model=='openai/gpt-4o-mini'
    finally:gateway.end_model_scope(token)


@pytest.mark.asyncio
@pytest.mark.parametrize('preset', ['fast','balanced','quality','configured'])
@pytest.mark.parametrize('followup',[False,True])
async def test_api_selection_persists_and_reaches_dispatch(monkeypatch,preset,followup):
    key='offline-owner-'+'x'*40
    monkeypatch.setattr(routes.settings,'deepdive_api_key',key)
    saved=[]
    async def save(run):saved.append(run)
    research=AsyncMock();monkeypatch.setattr(database,'save_run',save)
    monkeypatch.setattr(routes,'run_research',research)
    parent=ResearchRun(question='Parent fixture question')
    monkeypatch.setattr(routes,'load_run',AsyncMock(return_value=parent))
    app=FastAPI();app.include_router(routes.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        path='/runs/parent/follow-up' if followup else '/research'
        response=await client.post(path,json={'question':'A valid fixture question','model_preset':preset},headers={'X-DeepDive-API-Key':key})
        await asyncio.sleep(0)
        catalog=(await client.get('/model-presets')).json()
    assert response.status_code==200
    assert saved[0].model_preset==preset and len(saved[0].resolved_models)==12
    assert research.await_args.kwargs['model_preset']==preset
    assert catalog['default']=='balanced'
    assert all(p['est_cost_per_run'] is None and p['est_time'] is None for p in catalog['presets'].values())


@pytest.mark.asyncio
async def test_legacy_report_and_certificate_disclaimer_are_additive(monkeypatch):
    fixture=Path('tests/fixtures/action3-b23afbee4eda46e0.json');digest=hashlib.sha256(fixture.read_bytes()).hexdigest()
    run=ResearchRun.model_validate_json(fixture.read_text(encoding='utf-8'))
    assert run.model_preset is None
    monkeypatch.setattr(routes,'load_run',AsyncMock(return_value=run))
    app=FastAPI();app.include_router(routes.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        report=(await client.get('/runs/legacy/report')).json();certificate=(await client.get('/runs/legacy/certificate')).json();summary=(await client.get('/runs/legacy')).json()
    assert report['verification_disclaimer']==VERIFICATION_DISCLAIMER
    assert certificate['verification_disclaimer']==VERIFICATION_DISCLAIMER
    assert summary['model_preset'] is None
    assert report['report']==run.final_report and hashlib.sha256(fixture.read_bytes()).hexdigest()==digest

@pytest.mark.asyncio
async def test_scope_restores_after_exception_and_invalid_scope_does_not_change_it():
    gateway=MeshGateway()
    token=gateway.begin_model_scope('fast')
    try:
        with pytest.raises(ValueError):gateway.begin_model_scope('not-a-preset')
        assert gateway._preset.get()=='fast'
        nested=gateway.begin_model_scope('quality')
        try:
            raise RuntimeError('mocked stage failure')
        except RuntimeError:
            pass
        finally:gateway.end_model_scope(nested)
        assert gateway._preset.get()=='fast'
    finally:gateway.end_model_scope(token)
    assert gateway._preset.get() is None


def test_catalog_rates_are_snapshot_metadata_not_invented_run_estimates():
    from app.core.model_presets import preset_catalog
    data=preset_catalog()
    assert data['presets']['fast']['rates']['openai/gpt-4o-mini']['prompt_usd_per_1m']=='0.15000000'
    assert data['presets']['quality']['rates']['openai/gpt-4o']['completion_usd_per_1m']=='10.00000000'
    assert 'not billed' in data['pricing_note'] and all(not p['quality_verified'] for p in data['presets'].values())


def test_workflow_passes_preset_with_balanced_default():
    import json
    workflow=json.loads(Path('n8n/deepdive-research.json').read_text(encoding='utf-8'))
    node=next(n for n in workflow['nodes'] if n['name']=='Start Research Run')
    parameter=next(p for p in node['parameters']['bodyParameters']['parameters'] if p['name']=='model_preset')
    assert parameter['value']=="={{ $json.body.model_preset || 'balanced' }}"
