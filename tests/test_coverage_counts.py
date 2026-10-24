import json
import pytest
from app.agents.runner import run_coverage_analyst
from app.models.schemas import (ResearchRun, SubQuestion, Source, Evidence, AtomicClaim,
                                ClaimJudgement, ClaimVerdict)


@pytest.mark.asyncio
async def test_coverage_counts_stored_artifacts_not_model_guesses(monkeypatch):
    run = ResearchRun(question='Coverage fixture', confidence_threshold=0.8,
        sources=[Source(id='s1',url='https://fixture.example',trust_factors={'primary_source':True})],
        claims=[AtomicClaim(id='c1',text='Supported fact',subquestion_id='sq1',evidence_ids=['e1'])])
    subs=[SubQuestion(id='sq1',text='Answered area'), SubQuestion(id='sq2',text='Missing area')]
    evidence=[Evidence(id='e1',source_id='s1',subquestion_id='sq1',passage='Supported fact')]
    verdicts=[ClaimJudgement(claim_id='c1',verdict=ClaimVerdict.SUPPORTED,confidence=0.9,supporting_evidence_ids=['e1'])]
    async def complete(**kwargs):
        payload=json.loads(kwargs['user_prompt'])
        assert payload['verified_claims'][0]['id']=='c1'
        return {'coverage':[{'subquestion_id':'sq1','status':'green','verified_claim_count':0,'source_count':999},
                            {'subquestion_id':'invented','status':'green'}]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    result=await run_coverage_analyst(run,subs,evidence,verdicts,[])
    assert [r.subquestion_id for r in result]==['sq1','sq2']
    assert (result[0].verified_claim_count,result[0].source_count,result[0].evidence_count,result[0].primary_source_count)==(1,1,1,1)
    assert result[1].status.value=='red'


@pytest.mark.asyncio
async def test_no_green_area_without_accepted_claim_and_real_evidence(monkeypatch):
    run=ResearchRun(question='Coverage fixture',confidence_threshold=0.95,
        claims=[AtomicClaim(id='c',text='Below threshold',subquestion_id='sq',evidence_ids=['e'])],
        sources=[Source(id='s',url='https://fixture.example')])
    verdicts=[ClaimJudgement(claim_id='c',verdict=ClaimVerdict.SUPPORTED,confidence=0.9,supporting_evidence_ids=['e'])]
    async def complete(**kwargs):
        return {'coverage':[{'subquestion_id':'sq','status':'green','verified_claim_count':100}]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    result=await run_coverage_analyst(run,[SubQuestion(id='sq',text='Area')],
        [Evidence(id='e',source_id='s',subquestion_id='sq',passage='Fact')],verdicts,[])
    assert result[0].verified_claim_count==0
    assert result[0].status.value=='yellow'
