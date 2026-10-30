import { useEffect, useState } from 'react';

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail; } catch { /* non-JSON error */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function useApi<T>(path: string | null): { data: T | null; error: string | null; loading: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  useEffect(() => {
    if (!path) { setData(null); setLoading(false); return; }
    const ctrl = new AbortController();
    setLoading(true); setError(null); setData(null);
    fetchJson<T>(path, { signal: ctrl.signal }).then(setData).catch(e => {
      if (e.name !== 'AbortError') setError(e.message);
    }).finally(() => { if (!ctrl.signal.aborted) setLoading(false); });
    return () => ctrl.abort();
  }, [path]);
  return { data, error, loading };
}

export function query(path: string, params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)); });
  return `${path}?${q.toString()}`;
}
