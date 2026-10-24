import json

import pytest

from app.agents.runner import run_defense, run_judge
from app.models.schemas import AtomicClaim, DefenseArgument, Evidence, ResearchRun


@pytest.mark.asyncio
async def test_judge_reads_original_passage_and_not_fabricated_defense(monkeypatch):
    evidence = Evidence(id='e1', source_id='s1', passage='Revenue was 10 million in 2025.')
    claim = AtomicClaim(id='c1', text='Revenue was 20 million in 2025.', evidence_ids=['e1'])
    run = ResearchRun(question='Revenue?', evidence=[evidence])
    malicious_defense = DefenseArgument(claim_id='c1', supporting_passages=[
        {'evidence_id':'e1', 'passage_excerpt':'Revenue was 20 million in 2025.'},
    ])

    async def complete(**kwargs):
        payload = json.loads(kwargs['user_prompt'])
        assert payload['evidence'][0]['passage'] == evidence.passage
        assert payload['claims'][0]['evidence_ids'] == ['e1']
        assert payload['defense'][0]['supporting_passages'] == []
        return {'verdicts':[{'claim_id':'c1', 'verdict':'contradicted', 'confidence':0.95,
                             'contradicting_evidence_ids':['e1','invented']}]}

    monkeypatch.setattr('app.agents.runner.mesh.complete', complete)
    verdict = (await run_judge(run, [claim], [], [malicious_defense], 0.7))[0]
    assert verdict.verdict.value == 'contradicted'
    assert verdict.contradicting_evidence_ids == ['e1']


@pytest.mark.asyncio
async def test_missing_stored_passage_cannot_receive_supported_verdict(monkeypatch):
    claim = AtomicClaim(id='c1', text='Invented support', evidence_ids=['missing'])

    async def complete(**kwargs):
        return {'verdicts':[{'claim_id':'c1','verdict':'supported','confidence':1,
                            'supporting_evidence_ids':['missing']}]}

    monkeypatch.setattr('app.agents.runner.mesh.complete', complete)
    verdict = (await run_judge(ResearchRun(question='q'), [claim], [], [], 0.7))[0]
    assert verdict.verdict.value == 'unsupported'
    assert verdict.supporting_evidence_ids == []


@pytest.mark.asyncio
async def test_defense_keeps_only_real_cited_excerpt_with_whitespace_normalization(monkeypatch):
    evidence = [Evidence(id='e1', source_id='s1', passage='Revenue was\n10 million in 2025.'),
                Evidence(id='other', source_id='s2', passage='Another unrelated passage.')]
    claim = AtomicClaim(id='c1', text='Revenue was 10 million.', evidence_ids=['e1'])

    async def complete(**kwargs):
        return {'defenses':[{'claim_id':'c1','supporting_passages':[
            {'evidence_id':'e1','passage_excerpt':'Revenue was 10 million'},
            {'evidence_id':'e1','passage_excerpt':'Revenue was 20 million'},
            {'evidence_id':'other','passage_excerpt':'Another unrelated passage.'},
            {'evidence_id':'invented','passage_excerpt':'invented'},
            {'evidence_id':'e1','passage_excerpt':''},
        ]}]}

    monkeypatch.setattr('app.agents.runner.mesh.complete', complete)
    defense = (await run_defense(ResearchRun(question='q'), [claim], evidence))[0]
    assert defense.supporting_passages == [{'evidence_id':'e1','passage_excerpt':'Revenue was 10 million'}]
