import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { startTrace, finishTrace } from './trace';

export interface RunSummary { id: string; question: string; created_at: string; state: string }
export interface Source { id: string; url: string; title: string; trust_score: number; content_hash: string; retrieved_at: string; trust_factors: Record<string, unknown> }
export interface Evidence { id: string; source_id: string; subquestion_id: string; passage: string; passage_hash: string }
export interface Claim { id: string; text: string; evidence_ids: string[]; subquestion_id: string }
export interface Judgement { claim_id: string; verdict: string; confidence: number; explanation: string; missing_evidence: string; supporting_evidence_ids: string[]; contradicting_evidence_ids: string[] }
export interface Coverage { subquestion_id: string; subquestion_text: string; status: string; source_count: number; evidence_count: number; verified_claim_count: number }
export interface Contradiction { id: string; topic: string; claim_a: string; claim_b: string; evidence_a: string[]; evidence_b: string[]; resolution: string; explanation: string }
export interface AgentCall { cache_hit?: boolean; request_sent?: boolean | null; cache_source_call_id?: string; cached_prompt_tokens?: number | null; id: string; agent: string; model: string; duration_ms: number; success: boolean; prompt_tokens?: number | null; completion_tokens?: number | null; total_tokens?: number | null }
export interface Transition { from_state: string; to_state: string; timestamp: string; reason: string }
export interface Workspace { id: string; question: string; created_at: string; current_state: string; research_round: number; sources: Source[]; evidence: Evidence[]; claims: Claim[]; judgements: Judgement[]; coverage: Coverage[]; contradictions: Contradiction[]; state_transitions: Transition[]; agent_calls: AgentCall[]; final_report: string; error: string | null; warnings: string[]; accepted_claim_ids: string[]; confidence_threshold: number; certificate: Record<string, unknown> | null; subquestions: {id: string; text: string; completion_criteria: string}[] }
export interface ResearchInput { question: string; source_urls: string[]; max_rounds: number; confidence_threshold: number }
export const active = (state: string) => !['END', 'FAILED'].includes(state);
export interface Workspace {
  search_queries?: {id: string; subquestion_id: string; query: string; source_preference: string}[];
  search_audit?: Record<string, unknown>[];
  retrieval_audit?: Record<string, unknown>[];
  contradiction_audit?: Record<string, unknown>[];
  claim_selection_audit?: Record<string, unknown>[];
  report_grounding_status?: string;
  report_fallback_reason?: string;
  report_grounding_audit?: {unit_id: string; text: string; kept: boolean; included_in_final_report?: boolean; reason: string; method: string; prompt_version: string}[];
  coverage_derivation?: string;
  recorded_coverage?: Coverage[];
  prosecution?: {claim_id: string; weaknesses: string[]; unsupported_components: string[]}[];
  defense?: {claim_id: string; supporting_passages: Record<string, unknown>[]}[];
}
export const apiBase = (import.meta.env['VITE_API_URL'] || '').replace(/\/$/, '');
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const traceId = startTrace(path, init?.method || 'GET');
  const started = performance.now();
  let response: Response;
  try {
    response = await fetch(apiBase + path, {...init, headers: {'Content-Type': 'application/json', ...init?.headers}});
    finishTrace(traceId, response.status, performance.now() - started);
  } catch (error) {finishTrace(traceId, 'network error', performance.now() - started); throw error;}
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((item: {msg: string}) => item.msg).join('; ') : typeof detail === 'string' ? detail : `Request failed (${response.status})`);
  }
  return data as T;
}
export const runInterval = (data?: Workspace) => data && active(data.current_state) ? 4000 : false;
export function useRuns() { return useQuery({queryKey: ['runs'], queryFn: () => request<RunSummary[]>('/runs'), refetchInterval: query => query.state.data?.some(run => active(run.state)) ? 4000 : false}); }
export function useRun(id?: string) { return useQuery({queryKey: ['run', id], queryFn: () => request<Workspace>(`/runs/${encodeURIComponent(id!)}/workspace`), enabled: Boolean(id), refetchInterval: query => runInterval(query.state.data)}); }
export function useHealth() { return useQuery({queryKey: ['health'], queryFn: () => request<{status: string; mesh_configured: boolean; db_ok: boolean; version: string}>('/health'), refetchInterval: 30000}); }
export function useResearch(parentId?: string) {
  const client = useQueryClient();
  return useMutation({mutationFn: (input: ResearchInput) => request<{run_id: string; status: string}>(parentId ? `/runs/${encodeURIComponent(parentId)}/follow-up` : '/research', {method: 'POST', body: JSON.stringify(input)}), onSuccess: (result, input) => {
    client.setQueryData<RunSummary[]>(['runs'], old => [{id: result.run_id, question: input.question, state: 'START', created_at: new Date().toISOString()}, ...(old || [])]);
    void client.invalidateQueries({queryKey: ['runs']});
  }});
}
export function safeUrl(url: string): string | undefined { try { const parsed = new URL(url); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : undefined; } catch { return undefined; } }
