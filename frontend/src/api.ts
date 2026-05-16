export function apiBase(): string {
  const raw = typeof import.meta.env.VITE_API_BASE_URL === 'string'
    ? import.meta.env.VITE_API_BASE_URL.trim()
    : '';
  return raw.replace(/\/$/, '');
}

function url(path: string): string {
  const base = apiBase();
  return base ? `${base}${path}` : path;
}

export type Graph = { nodes: unknown[]; edges: unknown[] };

export async function fetchGraph(id: string): Promise<Graph> {
  const r = await fetch(url(`/api/graphs/${encodeURIComponent(id)}`));
  if (!r.ok) throw new Error(`fetchGraph ${r.status}`);
  return r.json();
}

export async function putGraph(id: string, body: Graph): Promise<void> {
  const r = await fetch(url(`/api/graphs/${encodeURIComponent(id)}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`putGraph ${r.status}`);
}

export type ServiceCheck = { ok: boolean; latency_ms?: number | null; error?: string | null };

export type Metrics = {
  status: 'healthy' | 'degraded' | 'unhealthy' | string;
  timestamp: string;
  uptime_seconds: number;
  service: string;
  dependencies: Record<string, ServiceCheck>;
  graph_count: number;
};

export async function fetchMetrics(): Promise<Metrics> {
  const r = await fetch(url('/api/metrics'));
  if (!r.ok) throw new Error(`metrics ${r.status}`);
  return r.json();
}
