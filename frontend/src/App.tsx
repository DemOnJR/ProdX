import { useEffect, useState } from 'react';
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from '@xyflow/react';

import '@xyflow/react/dist/style.css';

import { fetchGraph, fetchMetrics, putGraph, type Metrics } from './api';

const GRAPH_ID = 'prodx';

function StatusDot({ ok }: { ok: boolean | undefined }) {
  const cls = ok === true ? 'ok' : ok === false ? 'bad' : 'warn';
  return <span className={`dot ${cls}`} />;
}

function MetricsPanel() {
  const [m, setM] = useState<Metrics | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const data = await fetchMetrics();
        if (!stop) {
          setM(data);
          setErr(null);
        }
      } catch (e) {
        if (!stop) setErr(e instanceof Error ? e.message : 'error');
      }
    }
    void tick();
    const id = window.setInterval(tick, 5000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, []);

  return (
    <aside
      style={{
        width: 280,
        borderLeft: '1px solid var(--border)',
        background: 'var(--panel)',
        padding: 14,
        fontSize: 13,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14, letterSpacing: 0.4 }}>ProdX metrics</div>
      {err ? <div style={{ color: 'var(--bad)' }}>API unreachable: {err}</div> : null}
      {m ? (
        <>
          <div>
            <StatusDot ok={m.status === 'healthy'} />
            <strong>{m.status}</strong>{' '}
            <span style={{ color: 'var(--muted)' }}>· uptime {Math.round(m.uptime_seconds)}s</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(m.dependencies).map(([name, dep]) => (
              <div key={name}>
                <StatusDot ok={dep.ok} />
                {name}
                {dep.latency_ms != null ? (
                  <span style={{ color: 'var(--muted)' }}> · {dep.latency_ms} ms</span>
                ) : null}
                {dep.error ? <div style={{ color: 'var(--bad)', fontSize: 12 }}>{dep.error}</div> : null}
              </div>
            ))}
          </div>
          <div style={{ color: 'var(--muted)' }}>graphs stored: {m.graph_count}</div>
        </>
      ) : (
        <div style={{ color: 'var(--muted)' }}>loading…</div>
      )}
    </aside>
  );
}

function Canvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setErr(null);
    try {
      const g = await fetchGraph(GRAPH_ID);
      setNodes(Array.isArray(g.nodes) ? (g.nodes as Node[]) : []);
      setEdges(Array.isArray(g.edges) ? (g.edges as Edge[]) : []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'load failed');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    try {
      await putGraph(GRAPH_ID, { nodes, edges });
    } catch (e) {
      alert(e instanceof Error ? e.message : 'save failed');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
      <header
        style={{
          padding: '10px 14px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--panel)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <div>
          <strong style={{ fontSize: 15 }}>ProdX</strong>
          <span style={{ color: 'var(--muted)', marginLeft: 10 }}>
            graph <code>{GRAPH_ID}</code>
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="control" onClick={load} disabled={busy}>Reload</button>
          <button className="control" onClick={save} disabled={busy}>Save</button>
        </div>
      </header>
      {err ? (
        <div style={{ padding: 10, color: 'var(--bad)', background: '#1a0e0e', fontSize: 13 }}>
          {err}
        </div>
      ) : null}
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReactFlow
          colorMode="dark"
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.15 }}
        >
          <Background />
          <Controls />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div style={{ display: 'flex', height: '100vh', minHeight: 0 }}>
      <ReactFlowProvider>
        <Canvas />
      </ReactFlowProvider>
      <MetricsPanel />
    </div>
  );
}
