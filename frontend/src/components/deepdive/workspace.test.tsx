import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, it, vi } from 'vitest';
import { ResearchForm } from './ResearchForm';
import { AuditPanel, ContradictionsPanel, CourtroomPanel, ReportPanel, SourcesPanel } from './Panels';
import type { Workspace } from '@/lib/api';
import { ControlFlowPanel } from './ControlFlowPanel';
import { startTrace, finishTrace } from '@/lib/trace';

const run: Workspace = {id:'test-run',question:'What does the source support?',created_at:'2026-10-24T00:00:00Z',current_state:'END',research_round:1,confidence_threshold:0.7,accepted_claim_ids:['c1'],sources:[{id:'s1',url:'https://example.org',title:'Real source',trust_score:0.8,content_hash:'abc',retrieved_at:'2026-10-24',trust_factors:{}}],evidence:[{id:'e1',source_id:'s1',subquestion_id:'sq1',passage:'Exact source passage.',passage_hash:'def'}],claims:[{id:'c1',text:'Accepted claim',evidence_ids:['e1'],subquestion_id:'sq1'},{id:'c2',text:'Partial claim',evidence_ids:['e1'],subquestion_id:'sq1'}],judgements:[{claim_id:'c1',verdict:'supported',confidence:0.9,explanation:'Source supports it',missing_evidence:'',supporting_evidence_ids:['e1'],contradicting_evidence_ids:[]},{claim_id:'c2',verdict:'partially_supported',confidence:0.6,explanation:'Needs caveat',missing_evidence:'Scope',supporting_evidence_ids:['e1'],contradicting_evidence_ids:[]}],coverage:[],contradictions:[],state_transitions:[],agent_calls:[],final_report:'# Verified findings\nAccepted claim [claim:c1] [evidence:e1]',certificate:null,error:null,warnings:[],subquestions:[]};
const presetFixture = {default:'balanced',catalog_checked_at:'2026-10-25T15:20:32Z',pricing_note:'Catalog snapshot, not billing',presets:Object.fromEntries(['fast','balanced','quality','configured'].map(id => [id,{label:id,description:'Configured fixture routing',models:{heavy:'fixture/model'},rates:{'fixture/model':{prompt_usd_per_1m:'0.15',completion_usd_per_1m:'0.60'}},est_cost_per_run:null,est_time:null}]))};
const mockResearchFetch = (ok=true) => vi.fn().mockImplementation(async (path:string) => path.endsWith('/model-presets') ? {ok:true,json:async()=>presetFixture} : {ok,status:ok?200:503,json:async()=>ok?{run_id:'created',status:'started'}:{detail:'Backend unavailable'}});
afterEach(() => vi.unstubAllGlobals());
it('labels shared command documentation separately from recorded per-run queries', () => {
  render(<ControlFlowPanel run={run}/>);
  expect(screen.getByText('How commands travel · shared architecture')).toBeInTheDocument();
  expect(screen.getByText(/same for every research run/)).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Actual selected search queries'})).toBeInTheDocument();
});
it('explains single-source detection skip instead of implying agreement', () => {
  render(<ContradictionsPanel run={{...run,contradiction_audit:[{status:'skipped_single_source',compared_candidate_pairs:0,uncompared_candidate_pairs:0,rejected_candidates:0}]}} onCourtroom={vi.fn()}/>);
  expect(screen.getByRole('status')).toHaveTextContent('Cross-source detection skipped');
  expect(screen.getByText(/not evidence of consensus/)).toBeInTheDocument();
});
it('discloses unrecorded historical comparisons and partial token usage', () => {
  render(<ContradictionsPanel run={{...run,agent_calls:[
    {id:'one',agent:'contradiction_analyst',model:'Mesh/model',duration_ms:1,success:true,total_tokens:12},
    {id:'two',agent:'contradiction_analyst',model:'Mesh/model',duration_ms:1,success:true,total_tokens:null},
  ]}} onCourtroom={vi.fn()}/>);
  expect(screen.getByRole('status')).toHaveTextContent('not recorded for this historical run');
  expect(screen.getByText('12')).toBeInTheDocument();
  expect(screen.getByText(/1 recorded calls lack token usage/)).toBeInTheDocument();
});
it('shows both recorded source passages for a retained disagreement', () => {
  const inspect=vi.fn();
  render(<ContradictionsPanel run={{...run,
    evidence:[{id:'e1',source_id:'s1',subquestion_id:'sq1',passage:'Revenue was 10 million.',passage_hash:'a'},
              {id:'e2',source_id:'s2',subquestion_id:'sq1',passage:'Revenue was 20 million.',passage_hash:'b'}],
    sources:[...run.sources,{...run.sources[0]!,id:'s2',url:'https://example.net',title:'Other report'}],
    contradictions:[{id:'conflict',topic:'Revenue disagreement',claim_a:'10 million',claim_b:'20 million',
      evidence_a:['e1'],evidence_b:['e2'],resolution:'unresolved',explanation:'Comparable figures differ.'}],
  }} onCourtroom={inspect}/>);
  expect(screen.getByText('Revenue was 10 million.')).toBeInTheDocument();
  expect(screen.getByText('Revenue was 20 million.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Review courtroom verdicts'}));
  expect(inspect).toHaveBeenCalledOnce();
});
it('shows real search queries and labels missing historical retrieval traces', () => {
  render(<ControlFlowPanel run={{...run,search_queries:[{id:'q1',subquestion_id:'sq1',query:'official source query',source_preference:'primary'}]}}/>);
  expect(screen.getByText('official source query')).toBeInTheDocument();
  expect(screen.getByText(/historical run did not persist/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:/Search strategy/}));
  expect(screen.getByRole('heading',{name:'Selected stage · Search strategy'})).toBeInTheDocument();
});
it('shows actual API trace status and duration', () => {
  const id = startTrace('/runs/example/workspace','GET'); finishTrace(id,200,17);
  render(<ControlFlowPanel run={run}/>);
  expect(screen.getByText('/runs/example/workspace')).toBeInTheDocument();
  expect(screen.getByText('17 ms')).toBeInTheDocument();
});
it('opens real evidence from a report citation', () => {render(<ReportPanel run={run}/>); fireEvent.click(screen.getByRole('button',{name:'Inspect evidence e1'})); expect(screen.getByRole('heading',{name:'Evidence chain'})).toBeInTheDocument(); expect(screen.getAllByText('Exact source passage.').length).toBeGreaterThan(0); expect(screen.getByText(/Source supports it/)).toBeInTheDocument();});
it('filters courtroom and withholds partially supported claims', () => {render(<CourtroomPanel run={run}/>); fireEvent.change(screen.getByLabelText('Filter by verdict'), {target:{value:'partially_supported'}}); expect(screen.queryByText('Accepted claim')).not.toBeInTheDocument(); expect(screen.getByText('Partial claim')).toBeInTheDocument(); expect(screen.getByText('Withhold')).toBeInTheDocument();});
it('filters sources by trust without changing stored scores', () => {render(<SourcesPanel run={run}/>); fireEvent.change(screen.getByLabelText('Minimum trust'),{target:{value:'90'}}); expect(screen.getByText('No sources match this trust range.')).toBeInTheDocument();});
it('does not invent unmeasured audit scores', () => {render(<AuditPanel run={run}/>); expect(screen.getByText('Not measured')).toBeInTheDocument(); expect(screen.queryByText('94%')).not.toBeInTheDocument();});
it('submits validated research settings and selects created run', async () => {
  const fetchMock = mockResearchFetch(); vi.stubGlobal('fetch',fetchMock); const created=vi.fn();
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{mutations:{retry:false}}})}><ResearchForm open onClose={vi.fn()} onCreated={created}/></QueryClientProvider>);
  await vi.waitFor(()=>expect(screen.getByRole('option',{name:'quality'})).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText('Model preset'),{target:{value:'quality'}});
  fireEvent.change(screen.getByLabelText('Research access key'),{target:{value:'offline-test-access-key'}}); fireEvent.change(screen.getByLabelText('Question'),{target:{value:'A sufficiently detailed research question'}}); fireEvent.click(screen.getByRole('button',{name:'Start research'}));
  await vi.waitFor(() => expect(created).toHaveBeenCalledWith('created'));
  const post=fetchMock.mock.calls.find(call=>call[1]?.method==='POST')!;
  expect(JSON.parse(post[1].body)).toMatchObject({max_rounds:2,confidence_threshold:0.7,model_preset:'quality'});
  expect(post[1].headers['X-DeepDive-API-Key']).toBe('offline-test-access-key');
  expect(post[1].body).not.toContain('offline-test-access-key');
});
it('keeps server errors visible and restores submit control', async () => {
  vi.stubGlobal('fetch',mockResearchFetch(false));
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{mutations:{retry:false}}})}><ResearchForm open onClose={vi.fn()} onCreated={vi.fn()} initialQuestion="A sufficiently detailed research question"/></QueryClientProvider>);
  await vi.waitFor(()=>expect(screen.getByRole('option',{name:'balanced'})).toBeInTheDocument()); fireEvent.change(screen.getByLabelText('Research access key'),{target:{value:'offline-test-key'}}); fireEvent.click(screen.getByRole('button',{name:'Start research'})); expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable'); expect(screen.getByRole('button',{name:'Start research'})).toBeEnabled();
});

it('shows report review decisions and preserves missing historical diagnostics', () => {
  const first=render(<AuditPanel run={run}/>);
  expect(screen.getByText(/No report review decisions recorded/)).toBeInTheDocument();
  first.unmount();
  render(<AuditPanel run={{...run,report_grounding_audit:[
    {unit_id:'1',text:'Accepted statement',kept:true,reason:'Matches accepted claim',method:'model_review',prompt_version:'report-grounding-v1'},
    {unit_id:'2',text:'Unapproved extra detail',kept:false,reason:'Adds an unverified number',method:'model_review',prompt_version:'report-grounding-v1'},
  ]}}/>);
  expect(screen.getByText(/1 units kept/)).toHaveTextContent('1 units withheld');
  expect(screen.getByText('Withheld · report unit 2')).toBeInTheDocument();
  expect(screen.getByText('Adds an unverified number')).toBeInTheDocument();
});

it('labels partial fallback and model limitations in the report view', () => {
  render(<ReportPanel run={{...run,report_grounding_status:'accepted_claim_fallback',report_fallback_reason:'All generated prose withheld'}}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Partial accepted-claim fallback');
  expect(screen.getByText(/not a hallucination-free guarantee or independent human verification/)).toBeInTheDocument();
});

it('explains duplicate material skip without claiming source independence', () => {
  render(<ContradictionsPanel run={{...run,contradiction_audit:[{status:'skipped_same_material'}]}} onCourtroom={vi.fn()}/>);
  expect(screen.getByRole('status')).toHaveTextContent('probable duplicate publication material');
  expect(screen.getByRole('status')).toHaveTextContent('Different URLs do not provide independent corroboration');
});

it('labels local exact cache reuse without claiming a new provider request', () => {
  render(<AuditPanel run={{...run,agent_calls:[{id:'cached',agent:'judge',model:'Mesh/model',duration_ms:0,success:true,total_tokens:0,cache_hit:true,request_sent:false}]}}/>);
  expect(screen.getByText(/1 local exact-cache reuses/)).toBeInTheDocument();
  expect(screen.getAllByText('cached').length).toBeGreaterThan(0);
});

it('does not invent zero cache reuse for historical runs', () => {
  render(<AuditPanel run={{...run,agent_calls:[{id:'old',agent:'judge',model:'Mesh/model',duration_ms:5,success:true,cache_hit:null,total_tokens:null}]}}/>);
  expect(screen.getByText('Cache data not available for this run')).toBeInTheDocument();
});


it('shows safe search status and preserves unknown historical transport data', () => {
  render(<AuditPanel run={{...run,retrieval_audit:[{searches:[{query:'official source',status:'error',http_status:429,error_class:'HTTPStatusError',attempt_id:'attempt-search',duration_ms:12,timestamp:'2026-10-24'}],fetch_outcomes:[{url:'https://example.org',outcome:'failed',reason:'HTTPStatusError'}]}]}}/>);
  expect(screen.getByRole('heading',{name:'Search and retrieval outcomes'})).toBeInTheDocument();
  expect(screen.getByText(/HTTP: 429/)).toBeInTheDocument();
  expect(screen.getByText(/Attempt: attempt-search/)).toBeInTheDocument();
  expect(screen.getByText(/HTTP: Not recorded/)).toBeInTheDocument();
});

it('distinguishes cache lookup reasons and deterministic report artifacts from model review', () => {
  render(<AuditPanel run={{...run,agent_calls:[{id:'cache',agent:'judge',model:'Mesh/model',duration_ms:1,success:true,cache_hit:false,cache_miss_reason:'different_key',cache_store_status:'capacity_not_stored'}],report_artifact_audit:[{unit_id:'artifact-1',text:'Coverage area sq1: red; 0 passages.',method:'deterministic_artifact',based_on:'saved_run_counts_and_derived_coverage',included_in_final_report:true}]}}/>);
  expect(screen.getAllByText(/different_key.*capacity_not_stored/).length).toBeGreaterThan(0);
  expect(screen.getByRole('heading',{name:'Deterministic report limitations'})).toBeInTheDocument();
  expect(screen.getByText(/separate from model review/)).toBeInTheDocument();
});


it('shows submitted compacted query and numeric guard independently of model review', () => {
  render(<AuditPanel run={{...run,retrieval_audit:[{searches:[{query:'original long query',submitted_query:'short query',query_compacted:true,status:'success',http_status:200}]}],report_citation_audit:[{text:'Output fell 99%.',kept:false,method:'numeric_sentence_guard',issues:[{reason:'number_absent_from_local_cited_passages',sentence:'Output fell 99%.'}]}]}}/>);
  expect(screen.getByText(/Submitted query.*short query/)).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Sentence-level numeric citation checks'})).toBeInTheDocument();
  expect(screen.getByText('number_absent_from_local_cited_passages')).toBeInTheDocument();
});

it('requires owner access key without storing it in browser storage', async () => {
  const fetchMock=mockResearchFetch();vi.stubGlobal('fetch',fetchMock);
  render(<QueryClientProvider client={new QueryClient()}><ResearchForm open onClose={vi.fn()} onCreated={vi.fn()} initialQuestion="A sufficiently detailed research question"/></QueryClientProvider>);
  expect(screen.getByRole('button',{name:'Start research'})).toBeDisabled();
  const field=screen.getByLabelText('Research access key');
  expect(field).toHaveAttribute('type','password');
  await vi.waitFor(()=>expect(screen.getByRole('option',{name:'balanced'})).toBeInTheDocument());
  fireEvent.change(field,{target:{value:'offline-only-key'}});
  expect(screen.getByRole('button',{name:'Start research'})).toBeEnabled();
  expect(JSON.stringify(localStorage)).not.toContain('offline-only-key');
  expect(JSON.stringify(sessionStorage)).not.toContain('offline-only-key');
  expect(fetchMock.mock.calls.some(call=>call[1]?.method==='POST')).toBe(false);
});

it('keeps unknown historical presets explicit and disclaimer always visible', () => {
  const first=render(<ReportPanel run={run}/>);
  expect(screen.getByLabelText('Verification disclaimer')).toHaveTextContent('not a hallucination-free guarantee');
  first.unmount();
  render(<AuditPanel run={run}/>);
  expect(screen.getByText('Preset: Not recorded (historical)')).toBeInTheDocument();
});
it('shows token-rate snapshot without invented run-price promises', async () => {
  vi.stubGlobal('fetch',mockResearchFetch());
  render(<QueryClientProvider client={new QueryClient()}><ResearchForm open onClose={vi.fn()} onCreated={vi.fn()}/></QueryClientProvider>);
  expect(await screen.findByText(/Estimated run cost\/time: not calibrated/)).toBeInTheDocument();
  expect(screen.getByText(/fixture\/model:.*input.*output/)).toBeInTheDocument();
  expect(screen.queryByText(/45s|90s|0.30-0.50/)).not.toBeInTheDocument();
});
it('fails closed in the form when model metadata cannot load', async () => {
  vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline metadata failure')));
  render(<QueryClientProvider client={new QueryClient()}><ResearchForm open onClose={vi.fn()} onCreated={vi.fn()} initialQuestion="A sufficiently detailed research question"/></QueryClientProvider>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Model options unavailable');
  fireEvent.change(screen.getByLabelText('Research access key'),{target:{value:'offline-only-key'}});
  expect(screen.getByRole('button',{name:'Start research'})).toBeDisabled();
});
