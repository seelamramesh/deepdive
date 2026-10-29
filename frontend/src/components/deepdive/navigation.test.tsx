import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Dashboard } from './Dashboard';

const {run, navigate} = vi.hoisted(() => ({navigate:vi.fn(), run:{
  id:'navigation-fixture',question:'Navigation test fixture',created_at:'2026-10-24T00:00:00Z',
  current_state:'END',research_round:1,confidence_threshold:0.7,
  accepted_claim_ids:[],sources:[],evidence:[],claims:[],judgements:[],coverage:[],
  contradictions:[],state_transitions:[],agent_calls:[],subquestions:[],warnings:[],error:null,
  final_report:'',certificate:null,
}}));
vi.mock('@tanstack/react-router', () => ({useNavigate: () => navigate}));
vi.mock('@/lib/api', async importOriginal => ({
  ...await importOriginal<typeof import('@/lib/api')>(),
  useRuns: () => ({data:[{id:run.id,question:run.question,state:'END'}]}),
  useRun: () => ({data:run}),
  useHealth: () => ({data:{status:'ok',db_ok:true}}),
}));

it('exposes every view through a native selector and keeps active tabs in sync', () => {
  render(<Dashboard/>);
  const selector = screen.getByRole('combobox',{name:'Select research view'});
  expect(within(selector).getAllByRole('option')).toHaveLength(7);
  for (const view of ['Coverage','Courtroom','Audit','Contradictions','Sources','Control Flow','Report']) {
    fireEvent.change(selector,{target:{value:view}});
    expect(screen.getByRole('tab',{name:view})).toHaveAttribute('aria-selected','true');
    expect(screen.getByRole('tabpanel',{name:view})).toBeInTheDocument();
  }
});

it('opens searchable run controls and selects a run from the drawer', () => {
  render(<Dashboard/>);
  const button = screen.getByRole('button',{name:'Open research runs'});
  expect(button).toHaveTextContent('Runs');
  fireEvent.click(button);
  const drawer = screen.getByRole('dialog',{name:'Research runs'});
  fireEvent.change(within(drawer).getByRole('textbox',{name:'Search research runs'}),{target:{value:'not found'}});
  expect(within(drawer).getByText('No matching research runs.')).toBeInTheDocument();
  fireEvent.change(within(drawer).getByRole('textbox',{name:'Search research runs'}),{target:{value:''}});
  fireEvent.click(within(drawer).getByRole('button',{name:/Navigation test fixture/}));
  expect(navigate).toHaveBeenCalledWith({to:'/run/$runId',params:{runId:run.id}});
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
