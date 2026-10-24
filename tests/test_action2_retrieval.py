import json
import shutil
import subprocess
from pathlib import Path
import httpx
import pytest
from bs4 import BeautifulSoup
from app.models.schemas import Source,AtomicClaim,Evidence,ResearchRun,SubQuestion,ClaimJudgement,ClaimVerdict
from app.services import retrieval
from app.services.provenance import material_groups
from app.services.coverage import derive_coverage
from app.agents.runner import run_contradiction_analyst


def test_gap_query_moves_window_without_expanding_character_budget():
    snapshot="Revenue baseline. "*500 + "Checkpoint starvation single writer limitation. "*180
    first,start,end=retrieval.select_extraction_window(snapshot,"Revenue baseline")
    second,next_start,next_end=retrieval.select_extraction_window(snapshot,"Checkpoint starvation single writer limitation",previous_windows=[(start,end)])
    assert start==0 and next_start>0
    assert first!=second
    assert len(first)==len(second)==7000
    assert second==snapshot[next_start:next_end]


def test_shared_doi_groups_preprint_and_journal_without_merging_distinct_work():
    sources=[Source(id="journal",url="https://journal.example",work_identifiers=["doi:10.1234/example"]),
             Source(id="preprint",url="https://arxiv.example",work_identifiers=["doi:10.1234/example"]),
             Source(id="other",url="https://other.example",work_identifiers=["doi:10.1234/other"])]
    groups=material_groups(sources)
    assert groups['journal']==groups['preprint']
    assert groups['other']!=groups['journal']
    assert material_groups([Source(id='a',url='https://a.example'),Source(id='b',url='https://b.example')])=={'a':'a','b':'b'}


def test_doi_metadata_normalizes_without_inventing_dates_or_identity():
    soup=BeautifulSoup('<meta name="citation_doi" content="https://doi.org/10.1234/ABC"><meta name="prism.doi" content="10.1234/abc">','html.parser')
    assert retrieval.publication_identifiers(soup)==['doi:10.1234/abc']
    assert retrieval.publication_identifiers(BeautifulSoup('<title>Same title</title>','html.parser'))==[]


@pytest.mark.asyncio
async def test_shared_work_skips_detector_call_and_is_not_green_corroboration(monkeypatch):
    run=ResearchRun(question='Duplicate study',subquestions=[SubQuestion(id='sq',text='Finding')],
        sources=[Source(id=s,url='https://'+s+'.example',work_identifiers=['doi:10.1234/same']) for s in ['a','b']])
    run.evidence=[Evidence(id='e'+s,source_id=s,passage='Finding',subquestion_id='sq') for s in ['a','b']]
    run.claims=[AtomicClaim(id='c'+s,text='Finding',evidence_ids=['e'+s],subquestion_id='sq') for s in ['a','b']]
    run.judgements=[ClaimJudgement(claim_id=c.id,verdict=ClaimVerdict.SUPPORTED,confidence=.9,supporting_evidence_ids=c.evidence_ids) for c in run.claims]
    async def forbidden(**kwargs): raise AssertionError('Duplicate work must not spend detector call')
    monkeypatch.setattr('app.agents.runner.mesh.complete',forbidden)
    assert await run_contradiction_analyst(run,run.claims,run.evidence)==[]
    assert run.contradiction_audit[-1]['status']=='skipped_same_material'
    result=derive_coverage(run,[{'subquestion_id':'sq','status':'green'}])[0]
    assert result.source_count==2 and result.distinct_material_count==1
    assert result.status.value=='yellow'


@pytest.mark.parametrize('title,text,reason',[
    ('Checking your browser - reCAPTCHA','Please wait','browser_challenge_or_access_denied'),
    ('Consent required','Choose cookies','consent_wall'),
    ('404 Not Found','No article','error_page'),
    ('Article','Verify you are human before continuing','browser_challenge'),
    ('Using reCAPTCHA in an application','A normal tutorial with a cookie banner',None),
])
def test_unusable_page_classification_keeps_normal_articles(title,text,reason):
    assert retrieval.unusable_page_reason(title,text)==reason


@pytest.mark.asyncio
async def test_challenge_fetch_records_failure_and_never_becomes_a_source(monkeypatch):
    original=httpx.AsyncClient
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'text/html'},text='<title>Client Challenge</title><p>Verify you are human</p>'))
    monkeypatch.setattr(retrieval.httpx,'AsyncClient',lambda **kw:original(transport=transport,**kw))
    monkeypatch.setattr(retrieval,'validate_url',lambda url:(True,''))
    retrieval.drain_fetch_events()
    assert await retrieval.fetch_sources(['https://fixture.example/challenge'])==[]
    event=retrieval.drain_fetch_events()[0]
    assert event['outcome']=='unusable_material'
    assert event['reason']=='browser_challenge_or_access_denied'


def test_workflow_validation_handles_nonstring_questions_without_throwing():
    node=shutil.which('node')
    if not node: pytest.skip('Node not available')
    workflow=json.loads(Path('n8n/deepdive-research.json').read_text())
    assert len(workflow['nodes'])==14
    conditions=next(n for n in workflow['nodes'] if n['name']=='Validate Request')['parameters']['conditions']['conditions']
    expressions=[c['leftValue'][3:-2].strip() for c in conditions]
    program="const exprs="+json.dumps(expressions)+"; for(const body of [undefined,{}, {question:123},{question:{}},{question:[]},{question:'short'},{question:'A valid research question'}]) {const values=exprs.map(e=>new Function('$json','return ('+e+')')({body}));const valid=values[0]!==''&&values[1]>=10&&values[2]<=2000;if(valid!==(body?.question==='A valid research question'))throw Error('validation mismatch');}"
    subprocess.run([node,'-e',program],check=True,capture_output=True,text=True)


def test_publication_date_requires_explicit_valid_metadata():
    assert retrieval.publication_date_from_metadata(BeautifulSoup('<p>Updated 2026-10-24</p>','html.parser')) is None
    assert retrieval.publication_date_from_metadata(BeautifulSoup('<meta name="citation_publication_date" content="2025/04/16">','html.parser'))=='2025-04-16'
    assert retrieval.publication_date_from_metadata(BeautifulSoup('<meta name="citation_publication_date" content="2025-99-99">','html.parser')) is None


@pytest.mark.asyncio
async def test_critic_recency_is_unknown_without_recorded_date(monkeypatch):
    from app.agents.runner import run_source_critic
    async def complete(**kwargs):
        return {'scores':[{'source_id':'s','trust_score':.7,'factors':{'publication_recency':'recent'}}]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    result=await run_source_critic(ResearchRun(question='Date uncertainty'),[{'source_id':'s','publication_date':None}])
    assert result['s']['factors']['publication_recency']=='unknown'


def test_observed_journal_preprint_titles_form_a_probable_material_group():
    title='New Constraints on DMS and DMDS in the Atmosphere of K2-18 b from JWST MIRI'
    sources=[Source(id='j',url='https://iopscience.iop.org/article/10.3847/2041-8213/adc1c8',title=title+' - IOPscience'),
             Source(id='p',url='https://arxiv.org/abs/2504.12267',title='[2504.12267] '+title),
             Source(id='other',url='https://blog.example',title=title)]
    groups=material_groups(sources)
    assert groups['j']==groups['p']
    assert groups['other']!=groups['j']
    assert retrieval.unusable_page_reason('Radware Bot Manager Captcha','Please confirm you are a human')=='browser_challenge_or_access_denied'


@pytest.mark.asyncio
async def test_usable_fetch_preserves_metadata_snapshot_hash_and_audit(monkeypatch):
    original=httpx.AsyncClient
    html='<title>Research findings</title><meta name="citation_doi" content="10.1234/work"><meta name="citation_publication_date" content="2025-04-16"><p>Original reported research evidence.</p>'
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'text/html'},text=html))
    monkeypatch.setattr(retrieval.httpx,'AsyncClient',lambda **kw:original(transport=transport,**kw))
    monkeypatch.setattr(retrieval,'validate_url',lambda url:(True,''))
    retrieval.drain_fetch_events()
    source=(await retrieval.fetch_sources(['https://fixture.example/article']))[0]
    from app.models.schemas import _hash
    assert source.content_hash==_hash(source.content_snapshot)
    assert source.work_identifiers==['doi:10.1234/work']
    assert source.publication_date=='2025-04-16'
    assert retrieval.drain_fetch_events()[0]['outcome']=='retrieved'


@pytest.mark.asyncio
async def test_critic_duplicate_group_cannot_claim_independent_corroboration(monkeypatch):
    from app.agents.runner import run_source_critic
    async def complete(**kwargs):
        return {'scores':[{'source_id':s,'trust_score':.8,'factors':{'independence':True,'corroborated':True}} for s in ['a','b']]}
    monkeypatch.setattr('app.agents.runner.mesh.complete',complete)
    result=await run_source_critic(ResearchRun(question='Duplicate scoring'),[{'source_id':s,'material_group':'same'} for s in ['a','b']])
    for score in result.values():
        assert score['factors']['corroborated'] is False
        assert score['factors']['independence'] is False
        assert score['factors']['reported_corroborated'] is True
