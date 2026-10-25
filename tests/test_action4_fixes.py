import hashlib
import json
from pathlib import Path
import httpx
import pytest
from app.services import retrieval
from app.services.citation_checks import numeric_citation_issues, sentences
from app.models.schemas import ResearchRun, Evidence, AtomicClaim, ClaimJudgement, ClaimVerdict
from app.services.orchestrator import _verify_report_citations, _verified_claim_report

FIXTURE=Path(__file__).parent/'fixtures/action3-b23afbee4eda46e0.json'

@pytest.mark.parametrize('query',[
    ' '.join('term'+str(i) for i in range(80)),
    ' '.join(['word']*122),
    ' '.join(['abcdefghij']*61),
    'x'*610+' important evidence',
    '"keep this quoted phrase" '+' '.join('term'+str(i) for i in range(80)),
])
def test_query_compaction_never_cuts_words_or_exceeds_either_limit(query):
    compacted=retrieval.compact_search_query(query)
    assert len(compacted)<=600 and len(compacted.split())<=75
    assert compacted and all(word in query.split() for word in compacted.split())
    assert not ('x'*600 in compacted)

@pytest.mark.asyncio
async def test_compacted_query_is_logged_and_sent_only_to_mock(monkeypatch):
    original=httpx.AsyncClient;sent=[]
    def reply(request):sent.append(request.url.params['q']);return httpx.Response(422,json={'not_logged':'private response'})
    monkeypatch.setattr(retrieval.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(reply),**kw))
    monkeypatch.setattr(retrieval.settings,'brave_search_api_key','not-a-real-key')
    query=' '.join('term'+str(i) for i in range(80))
    retrieval.drain_search_events();assert await retrieval.search_web(query)==[]
    event,=retrieval.drain_search_events()
    assert event['original_query']==query and event['submitted_query']==sent[0]
    assert event['query_compacted'] and event['submitted_words']<=75
    assert event['status']=='error' and event['http_status']==422
    assert 'private response' not in json.dumps(event)

@pytest.mark.asyncio
async def test_uncompactable_query_never_dispatches(monkeypatch):
    monkeypatch.setattr(retrieval.settings,'brave_search_api_key','not-a-real-key')
    retrieval.drain_search_events();assert await retrieval.search_web('x'*610)==[]
    event,=retrieval.drain_search_events()
    assert event['status']=='invalid_query' and event['request_sent'] is False


def test_action3_fixture_numeric_sentence_cannot_borrow_paragraph_citation():
    before=hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    run=ResearchRun.model_validate_json(FIXTURE.read_text(encoding='utf-8'))
    offending=next(unit['text'] for unit in run.report_grounding_audit if unit['unit_id']=='7')
    _verify_report_citations(run)
    assert offending not in run.final_report
    assert any(issue['reason']=='numeric_sentence_missing_local_citations' for event in run.report_citation_audit for issue in event['issues'])
    assert '18%' in run.final_report and '[evidence:6da09bb0c613]' in run.final_report
    assert 'Run limitations (recorded artifacts)' in run.final_report
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest()==before


def test_wrong_numeric_passage_is_rejected_even_if_judge_link_is_allowed():
    evidence={'e':Evidence(id='e',source_id='s',passage='Workers were assigned randomly.')}
    issues=numeric_citation_issues('Output fell 18% [claim:c] [evidence:e].',evidence,{('c','e')})
    assert issues[0]['reason']=='number_absent_from_local_cited_passages'

@pytest.mark.parametrize('line',[
    'Output fell 18%. [claim:c] [evidence:e] The method was randomized.',
    'Output fell 18% [claim:c] [evidence:e]. The method was randomized.',
    'Output fell 18 percent [claim:c] [evidence:e].',
    'The U.S. rate was 1.8% [claim:c] [evidence:e].',
])
def test_sentence_boundaries_keep_postfix_citations_decimals_and_abbreviations(line):
    evidence={'e':Evidence(id='e',source_id='s',passage='Output fell 18 percent. The U.S. rate was 1.8%.')}
    assert not numeric_citation_issues(line,evidence,{('c','e')})


def test_fallback_cites_all_approved_passages_and_cannot_reintroduce_wrong_number():
    run=ResearchRun(question='Numeric fallback')
    run.evidence=[Evidence(id='design',source_id='s',passage='A randomized trial in India.'),Evidence(id='number',source_id='s',passage='Productivity was 18% lower.')]
    run.claims=[AtomicClaim(id='c',text='Productivity in the Indian trial was 18% lower.',evidence_ids=['design','number'])]
    run.judgements=[ClaimJudgement(claim_id='c',verdict=ClaimVerdict.SUPPORTED,confidence=.9,supporting_evidence_ids=['design','number'])]
    report=_verified_claim_report(run,run.supported_claims(.7))
    assert '[evidence:design]' in report and '[evidence:number]' in report
    run.claims[0].text='Productivity was 99% lower.'
    report=_verified_claim_report(run,run.supported_claims(.7))
    assert '99%' not in report


def test_statistic_heading_cannot_bypass_numeric_check():
    run=ResearchRun(question='Check heading')
    run.evidence=[Evidence(id='e',source_id='s',passage='Observed output was 18%.')]
    run.claims=[AtomicClaim(id='c',text='Output was 18%.',evidence_ids=['e'])]
    run.judgements=[ClaimJudgement(claim_id='c',verdict=ClaimVerdict.SUPPORTED,confidence=.9,supporting_evidence_ids=['e'])]
    run.final_report='# Report\n## 99% improvement\nOutput was 18% [claim:c] [evidence:e].'
    _verify_report_citations(run)
    assert '99%' not in run.final_report and '18%' in run.final_report
