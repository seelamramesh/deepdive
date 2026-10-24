import { useSyncExternalStore } from 'react';

export interface RequestTrace {id: number; method: string; path: string; startedAt: string; duration: number | null; status: number | 'pending' | 'network error'}
let events: RequestTrace[] = [];
let sequence = 0;
const listeners = new Set<() => void>();
function emit() {listeners.forEach(listener => listener());}
export function startTrace(path: string, method: string) {
  const id = ++sequence;
  events = [...events.slice(-49), {id, path, method, startedAt:new Date().toISOString(), duration:null, status:'pending'}];
  emit(); return id;
}
export function finishTrace(id: number, status: RequestTrace['status'], duration: number) {
  events = events.map(event => event.id === id ? {...event,status,duration:Math.round(duration)} : event); emit();
}
export function useRequestTrace() {
  return useSyncExternalStore(listener => {listeners.add(listener); return () => {listeners.delete(listener);};}, () => events, () => events);
}
