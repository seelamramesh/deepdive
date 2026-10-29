import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AuditPanel, CourtroomPanel, CoveragePanel, ReportPanel } from './Panels';
import { useIsMobile } from '@/lib/use-mobile';
import type { Workspace } from '@/lib/api';

const run: Workspace = {
  id: 'mobile-fixture', question: 'Mobile layout fixture, not live research',
  created_at: '2026-10-24T00:00:00Z', current_state: 'END', research_round: 1,
  confidence_threshold: 0.7, accepted_claim_ids: [], sources: [], evidence: [],
  claims: [{id:'c1', text:'A claim awaiting verification', evidence_ids:[], subquestion_id:'sq1'}],
  judgements: [], coverage: [], contradictions: [], state_transitions: [],
  agent_calls: [
    {id:'a1',agent:'planner',model:'Mesh/model',duration_ms:25,success:true,total_tokens:0},
    {id:'a2',agent:'judge',model:'Mesh/model',duration_ms:50,success:false,total_tokens:null},
  ],
  final_report:'', certificate:null, error:null, warnings:[], subquestions:[],
};

function mobileMedia() {
  let matches = true;
  const listeners = new Set<() => void>();
  vi.stubGlobal('matchMedia', vi.fn(() => ({get matches() {return matches;},
    addEventListener: (_event: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_event: string, listener: () => void) => listeners.delete(listener),
  })));
  return {resize(value: boolean) {act(() => {matches = value; listeners.forEach(fn => fn());});}, listeners};
}
afterEach(() => vi.unstubAllGlobals());

it('switches mobile subscription at the breakpoint and cleans up listeners', () => {
  const media = mobileMedia();
  function Probe() {return <p>{useIsMobile() ? 'mobile' : 'desktop'}</p>;}
  const view = render(<Probe/>);
  expect(screen.getByText('mobile')).toBeInTheDocument();
  media.resize(false);
  expect(screen.getByText('desktop')).toBeInTheDocument();
  view.unmount(); expect(media.listeners.size).toBe(0);
});

it('collapses the mobile library and restores desktop aside on resize', () => {
  const media = mobileMedia(); render(<ReportPanel run={run}/>);
  const summary = screen.getByText('Sources (0) · Evidence library (0)');
  expect(summary.closest('details')).not.toHaveAttribute('open');
  fireEvent.click(summary);
  expect(summary.closest('details')).toHaveAttribute('open');
  media.resize(false);
  expect(screen.queryByText('Sources (0) · Evidence library (0)')).not.toBeInTheDocument();
  expect(screen.getByRole('complementary')).toHaveTextContent('Evidence library');
});

it('keeps unknown confidence honest and withholds unverified mobile claims', () => {
  mobileMedia(); render(<CourtroomPanel run={run}/>);
  expect(screen.getByText('Confidence: Not recorded')).toBeInTheDocument();
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  expect(screen.getByText('A claim awaiting verification').closest('summary')).toHaveTextContent('Withhold');
});

it('renders recorded zero tokens distinctly from unknown in audit cards', () => {
  mobileMedia(); render(<AuditPanel run={run}/>);
  const cards = screen.getByLabelText('Agent call cards');
  expect(within(cards).getByText('0')).toBeInTheDocument();
  expect(within(cards).getByText('Not recorded')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', {name:'Sort by duration'}));
  expect(within(cards).getAllByRole('article')[0]).toHaveTextContent('judge');
});

it('preserves zero evidence and gap follow-up in coverage details', () => {
  mobileMedia(); const follow = vi.fn();
  render(<CoveragePanel run={{...run,coverage:[{subquestion_id:'sq1',subquestion_text:'Unanswered area',status:'red',source_count:0,evidence_count:0,verified_claim_count:0}]}} onResearch={follow}/>);
  fireEvent.click(screen.getByRole('button',{name:'Request more research'}));
  expect(follow).toHaveBeenCalledWith(expect.stringContaining('Unanswered area'));
});
