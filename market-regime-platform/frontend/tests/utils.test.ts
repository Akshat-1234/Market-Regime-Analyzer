import { describe, expect, it, vi } from 'vitest';
import { evidence, pct, num, shortDate, signed, stateName } from '../src/utils';
import { fetchJson } from '../src/api';

describe('honest formatting and interpretation',()=>{
  it('handles missing numeric values and signs',()=>{
    expect(pct(null)).toBe('—');expect(num(Infinity)).toBe('—');expect(pct(.172)).toBe('17.2%');
    expect(signed(.0014)).toBe('+0.001');expect(signed(-.1887)).toBe('-0.189');
  });
  it('does not equate a zero-spanning interval with a demonstrated edge',()=>{
    expect(evidence([{control:'Trend',lower:-.19,upper:.18}])).toBe('INTERVAL INCLUDES ZERO');
    expect(evidence([{control:'Trend',lower:.01,upper:.2}])).toBe('INTERVAL EXCLUDES ZERO');
    expect(evidence([])).toBe('INTERVAL UNAVAILABLE');
  });
  it('labels local state ranks correctly in two- and three-state models',()=>{
    expect(stateName(1,2)).toBe('HIGHER VOL');expect(stateName(1,3)).toBe('MIDDLE VOL');
    expect(shortDate('2026-10-22')).toBe('22 Oct 2026');
  });
  it('surfaces server validation errors',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:422,json:async()=>({detail:'Bad date range'})}));
    await expect(fetchJson('/api/test')).rejects.toThrow('Bad date range');vi.unstubAllGlobals();
  });
});
