"""Full API -> real agents/gateway/orchestrator -> SQLite -> report with fake I/O.

These are deterministic integration fixtures, not live provider quality evaluations.
"""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from app.agents import prompts
from app.services.report_grounding import REPORT_REVIEW_PROMPT
from app.api import routes
from app.core.mesh_gateway import mesh
from app.models.schemas import Source, _hash
from app.storage import database


@pytest.mark.asyncio
@pytest.mark.parametrize('cache_enabled', [False, True])
@pytest.mark.parametrize('scenario', ['supported_and_withheld', 'gap_then_recover', 'malformed_synthesis', 'no_sources', 'tampered_snapshot', 'long_snapshot', 'late_relevant_snapshot'])
async def test_offline_api_research_to_persisted_report(monkeypatch, tmp_path, scenario, cache_enabled):
    monkeypatch.setattr('app.core.mesh_gateway.settings.mesh_run_cache', cache_enabled)
    monkeypatch.setattr(database, 'DB_PATH', str(tmp_path/'runs.db'))
    await database.init_db()
    passage = 'Fixture revenue was 10 million in 2025.'
    snapshot = passage + ('\n' + 'x'*9000 if scenario == 'long_snapshot' else '')
    if scenario == 'late_relevant_snapshot':
        snapshot = 'Unrelated navigation. ' * 600 + passage + ' Other content.' * 500
    late_gap = 'Fixture revenue has a publication date.'
    if scenario == 'gap_then_recover':
        snapshot = passage + '\n' + 'x'*9000 + '\n' + late_gap
    source = Source(id='source',url='https://fixture.example/revenue',title='Offline fixture',
                    content_hash=_hash(snapshot),content_snippet=snapshot[:500],
                    content_snapshot='Tampered contents' if scenario=='tampered_snapshot' else snapshot)
    search_count = 0
    coverage_count = 0
    source_fetches = 0
    researcher_count = 0

    async def search(query):
        return [] if scenario == 'no_sources' else [source.url]

    async def sources(urls):
        nonlocal source_fetches
        source_fetches += 1
        return [source] if urls else []

    monkeypatch.setattr('app.services.orchestrator.search_web', search)
    monkeypatch.setattr('app.services.orchestrator.fetch_sources', sources)

    class Completions:
        async def create(self, **kwargs):
            nonlocal search_count, coverage_count, researcher_count
            system = kwargs['messages'][0]['content']
            raw = kwargs['messages'][1]['content']
            payload = {} if system == prompts.PLANNER_PROMPT else json.loads(raw)
            if system == prompts.PLANNER_PROMPT:
                result = {'subquestions':[{'text':'What was fixture revenue?','completion_criteria':'Exact revenue and date'}]}
            elif system == prompts.SEARCH_STRATEGIST_PROMPT:
                search_count += 1
                result = {'queries':[{'subquestion_id':payload['subquestions'][0]['id'],'query':f'fixture query {search_count}'}]}
            elif system == prompts.RESEARCHER_PROMPT:
                researcher_count += 1
                if scenario == 'gap_then_recover' and researcher_count == 2:
                    assert late_gap in payload['sources'][0]['content']
                    assert payload['sources'][0]['content'] != snapshot[:7000]
                elif scenario == 'late_relevant_snapshot':
                    assert passage not in snapshot[:7000]
                    assert passage in payload['sources'][0]['content']
                    assert len(payload['sources'][0]['content']) == 7000
                else:
                    assert payload['sources'][0]['content'] == snapshot[:7000]
                result = {'evidence':[{'source_id':payload['sources'][0]['source_id'],
                                      'subquestion_id':payload['subquestions'][0]['id'], 'passage':passage}]}
                if scenario == 'gap_then_recover' and researcher_count == 2:
                    result = {'evidence':[]}
            elif system == prompts.SOURCE_CRITIC_PROMPT:
                assert scenario != 'tampered_snapshot', 'Tampered snapshot must not reach critic'
                scored = payload['sources'][0]
                assert (late_gap if scenario == 'gap_then_recover' and researcher_count == 2 else passage) in scored['selected_content']
                assert scored['content_scope'] == 'partial_snapshot_window'
                assert scored['selected_content'] == snapshot[scored['snapshot_start']:scored['snapshot_end']]
                assert scored['snapshot_hash'] == _hash(snapshot)
                if scenario == 'late_relevant_snapshot':
                    assert scored['snapshot_start'] > 0
                    assert passage not in scored['content_snippet']
                result = {'scores':[{'source_id':'source','trust_score':0.9,'factors':{'primary_source':True}}]}
            elif system == prompts.CLAIM_DRAFTER_PROMPT:
                result = {'claims':[{'text':text,'evidence_ids':[payload['evidence'][0]['id']],
                                     'subquestion_id':payload['subquestions'][0]['id']}
                                    for text in [passage,'Fixture revenue was 20 million in 2025.']]}
            elif system == prompts.PROSECUTOR_PROMPT:
                result = {'arguments':[{'claim_id':c['id'],'weaknesses':['Compare original number']} for c in payload['claims']]}
            elif system == prompts.DEFENSE_PROMPT:
                result = {'defenses':[{'claim_id':c['id'],'supporting_passages':[
                    {'evidence_id':c['evidence_ids'][0],'passage_excerpt':c['text']}]} for c in payload['claims']]}
            elif system == prompts.JUDGE_PROMPT:
                assert payload['evidence'][0]['passage'] == passage
                assert all('20 million' not in str(d['supporting_passages']) for d in payload['defense'])
                result = {'verdicts':[{'claim_id':c['id'],'verdict':'supported' if c['text']==passage else 'contradicted',
                                      'confidence':0.95,'supporting_evidence_ids':c['evidence_ids'] if c['text']==passage else [],
                                      'contradicting_evidence_ids':[] if c['text']==passage else c['evidence_ids'],
                                      'explanation':'Compared original fixture passage.'} for c in payload['claims']]}
            elif system == prompts.CONTRADICTION_ANALYST_PROMPT:
                result = {'contradictions':[]}
            elif system == prompts.COVERAGE_ANALYST_PROMPT:
                coverage_count += 1
                result = {'coverage':[{'subquestion_id':payload['subquestions'][0]['id'],
                                      'subquestion_text':'Fixture revenue','status':'red' if scenario=='gap_then_recover' and coverage_count==1 else 'green'}]}
            elif system == REPORT_REVIEW_PROMPT:
                result = {'decisions':[{'unit_id':u['unit_id'],'supported':True,'reason':'Fixture review'} for u in payload['units']]}
            elif system == prompts.SYNTHESIZER_PROMPT:
                if scenario == 'malformed_synthesis':
                    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='```json {'),finish_reason='length')],
                                           usage=SimpleNamespace(prompt_tokens=10,completion_tokens=2,total_tokens=12))
                claim = payload['supported_claims'][0]
                result = {'report':f"# Fixture report\n## Findings\n{claim['text']} [claim:{claim['id']}] [evidence:{claim['evidence_ids'][0]}]"}
            else:
                raise AssertionError('Unexpected agent')
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(result)),finish_reason='stop')],
                                   usage=SimpleNamespace(prompt_tokens=10,completion_tokens=2,total_tokens=12))

    monkeypatch.setattr(mesh, '_client', SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
    app = FastAPI()
    app.include_router(routes.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response = await client.post('/research',json={'question':('What was fixture revenue in 2025?' if scenario == 'late_relevant_snapshot' else f'Offline fixture scenario {scenario}'), 'max_rounds':2 if scenario=='gap_then_recover' else 1})
        assert response.status_code == 200
        run_id = response.json()['run_id']
        task = routes._running.get(run_id)
        if task:
            await asyncio.wait_for(task, timeout=10)
        workspace = (await client.get(f'/runs/{run_id}/workspace')).json()
        assert workspace['current_state'] == 'END', workspace.get('error')
        assert workspace['final_report'].strip()
        assert workspace['agent_calls']
        assert all(call['total_tokens'] == (0 if call.get('cache_hit') else 12) for call in workspace['agent_calls'])
        assert all(call.get('request_sent') is False for call in workspace['agent_calls'] if call.get('cache_hit'))
        assert all('response_preview' not in call for call in workspace['agent_calls'])
        saved = await database.load_run(run_id)
        assert len(saved.agent_calls) == len(workspace['agent_calls'])
        assert all('content_snapshot' not in item for item in workspace['sources'])
        if scenario in ('no_sources', 'tampered_snapshot'):
            assert not workspace['accepted_claim_ids']
            assert 'Insufficient verified evidence' in workspace['final_report']
        else:
            assert len(workspace['accepted_claim_ids']) == 1
            assert '20 million' not in workspace['final_report']
            assert '[evidence:' in workspace['final_report']
            assert all(e['source_snapshot_hash']==_hash(snapshot) for e in workspace['evidence'])
            assert saved.sources[0].content_snapshot == snapshot
            extraction = workspace['retrieval_audit'][0]['extraction_inputs'][0]
            assert extraction['snapshot_hash'] == _hash(snapshot)
            start, end = extraction['snapshot_start'], extraction['snapshot_end']
            assert extraction['analyzed_content_hash'] == _hash(snapshot[start:end])
            assert extraction['selection_policy'] == 'gap_lexical_window_v2'
            if scenario == 'late_relevant_snapshot':
                assert start > 0
                assert passage in snapshot[start:end]
            else:
                assert start == 0
        assert source_fetches == (0 if scenario=='no_sources' else 1)
        if scenario == 'tampered_snapshot':
            assert any('hash mismatch' in warning for warning in workspace['warnings'])
        if scenario == 'gap_then_recover':
            assert workspace['research_round'] == 2
            assert any(call.get('cache_hit') for call in workspace['agent_calls']) is cache_enabled
            first_window = workspace['retrieval_audit'][0]['extraction_inputs'][0]
            later_window = workspace['retrieval_audit'][1]['extraction_inputs'][0]
            assert first_window['snapshot_start'] == 0
            assert later_window['snapshot_start'] > 0
            assert later_window['characters_sent'] <= 7000
            assert later_window['selection_query'] != first_window['selection_query']
            assert later_window['previous_windows']
            assert any(t['to_state']=='RESEARCH_GAPS' for t in workspace['state_transitions'])
        if scenario == 'malformed_synthesis':
            assert workspace['warnings']
            assert sum(not c['success'] for c in workspace['agent_calls']) == 2
