import { afterEach, describe, expect, it, vi } from 'vitest';
import { active, request, runInterval, safeUrl, type Workspace } from './api';
afterEach(() => vi.unstubAllGlobals());
describe('API contracts', () => {
  it('polls only active runs', () => {expect(runInterval({current_state:'SEARCH'} as Workspace)).toBe(4000); expect(runInterval({current_state:'END'} as Workspace)).toBe(false); expect(active('FAILED')).toBe(false);});
  it('surfaces validation errors', async () => {vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok:false,status:422,json:async () => ({detail:[{msg:'Question too short'}]})})); await expect(request('/research')).rejects.toThrow('Question too short');});
  it('rejects unsafe citation URLs', () => {expect(safeUrl('javascript:alert(1)')).toBeUndefined(); expect(safeUrl('data:text/html,bad')).toBeUndefined(); expect(safeUrl('https://example.org/a')).toBe('https://example.org/a');});
});
