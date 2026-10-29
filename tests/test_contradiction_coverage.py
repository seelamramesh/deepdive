import json
import pytest
from app.agents.runner import run_contradiction_analyst
from app.models.schemas import AtomicClaim, Evidence, ResearchRun


def artifacts(count=7, distinct=False):
    claims=[AtomicClaim(id=f'c{i}',text=f'Claim {i}',subquestion_id='sq',evidence_ids=[f'e{i}']) for i in range(count)]
    evidence=[Evidence(id=f'e{i}',source_id=f's{i}' if distinct else ('a' if i<6 else 'b'),passage=f'Passage {i}') for i in range(count)]
    return claims,evidence


@pytest.mark.asyncio
async def test_only_one_source_skips_paid_detector_with_explicit_reason(monkeypatch):
    claims,evidence=artifacts(6)
    async def forbidden(**kwargs):
        raise AssertionError('No meaningful cross-source pair; should not call Mesh')
    monkeypatch.setattr('app.agents.runner.mesh.complete',forbidden)
    run=ResearchRun(question='Single-source fixture')
    assert await run_contradiction_analyst(run,claims,evidence)==[]
    assert run.contradiction_audit[-1]['status']=='skipped_single_source'


@pytest.mark.asyncio
async def test_cross_batch_pair_reaches_detector_and_is_retained(monkeypatch):
    claims,evidence=artifacts()
    checked=[]
    async def complete(**kwargs):
        payload=json.loads(kwargs['user_prompt']);ids={c['id'] for c in payload['claims']};checked.append(ids)
        return {'contradictions':[{'topic':'Same metric disagreement','claim_a':'Claim 5','claim_b':'Claim 6',
            'evidence_a':['e5'],'evidence_b':['e6'],'explanation':'Different sources disagree.'}]} if {'c5','c6'}<=ids else {'contradictions':[]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    run=ResearchRun(question='Cross-batch fixture')
    result=await run_contradiction_analyst(run,claims,evidence)
    assert any({'c5','c6'}<=ids for ids in checked)
    assert len(result)==1
    assert run.contradiction_audit[-1]['uncompared_candidate_pairs']==0


@pytest.mark.asyncio
async def test_budget_limit_is_disclosed_not_called_no_disagreement(monkeypatch):
    claims,evidence=artifacts(8,distinct=True)
    async def complete(**kwargs):return {'contradictions':[]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    monkeypatch.setattr('app.agents.runner.settings.max_contradiction_batches',1)
    run=ResearchRun(question='Bounded fixture')
    await run_contradiction_analyst(run,claims,evidence)
    audit=run.contradiction_audit[-1]
    assert audit['status']=='limited_comparison'
    assert audit['uncompared_candidate_pairs']>0
    assert len(audit['batches'])==1


@pytest.mark.asyncio
async def test_invalid_refs_and_same_source_results_are_counted_not_retained(monkeypatch):
    claims,evidence=artifacts()
    async def complete(**kwargs):
        return {'contradictions':[
            {'evidence_a':['invented'],'evidence_b':['e6']},
            {'evidence_a':['e0'],'evidence_b':['e1']},
        ]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    run=ResearchRun(question='Invalid candidates fixture')
    assert await run_contradiction_analyst(run,claims,evidence)==[]
    assert run.contradiction_audit[-1]['rejected_candidates']>0


@pytest.mark.asyncio
async def test_topic_rewording_does_not_double_count_same_pair_across_rounds(monkeypatch):
    claims,evidence=artifacts(2,distinct=True)
    titles=iter(['Value disagreement','Conflicting values'])
    async def complete(**kwargs):
        return {'contradictions':[{'topic':next(titles),'claim_a':'Claim 0','claim_b':'Claim 1',
                                   'evidence_a':['e0'],'evidence_b':['e1'],'type':'numeric'}]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    run=ResearchRun(question='Stable identity fixture')
    run.contradictions=await run_contradiction_analyst(run,claims,evidence)
    result=await run_contradiction_analyst(run,claims,evidence)
    assert len(result)==1


@pytest.mark.asyncio
async def test_every_returned_candidate_is_accounted_for(monkeypatch):
    claims,evidence=artifacts(4,distinct=True)
    async def complete(**kwargs):
        return {'contradictions':[{'topic':f'Conflict {a}-{b}','claim_a':f'Claim {a}','claim_b':f'Claim {b}',
                                    'evidence_a':[f'e{a}'],'evidence_b':[f'e{b}'],'type':'numeric'}
                                   for a,b in [(0,1),(0,2),(0,3),(1,2)]]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    run=ResearchRun(question='Full response audit fixture')
    result=await run_contradiction_analyst(run,claims,evidence)
    assert len(result)==4
    assert run.contradiction_audit[-1]['batches'][0]['returned_candidates']==4
