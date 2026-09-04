import { useEffect, useRef, useState } from "react";
import { statusWebSocketUrl } from "../api";
import type { StatusSnapshot } from "../types";

const EMPTY: StatusSnapshot = { queued: 0, running: 0, success: 0, failed: 0, total: 0, running_task_run_ids: [] };

export function LiveStatus({ onPreview }: { onPreview: (taskRunId: string) => void }) {
  const [status, setStatus] = useState<StatusSnapshot>(EMPTY);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;

    function connect() {
      const ws = new WebSocket(statusWebSocketUrl());
      socketRef.current = ws;

      ws.onopen = () => !cancelled && setConnected(true);
      ws.onmessage = (event) => !cancelled && setStatus(JSON.parse(event.data));
      ws.onclose = () => {
        if (cancelled) return;
        setConnected(false);
        retryTimer = window.setTimeout(connect, 2000); // dashboard reopened, server restarted, etc.
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      cancelled = true;
      window.clearTimeout(retryTimer);
      socketRef.current?.close();
    };
  }, []);

  return (
    <section className="panel">
      <h2>Live Visitor Status {connected ? <span className="dot dot-live" /> : <span className="dot dot-off" />}</h2>
      <div className="status-grid">
        <StatusTile label="Running" value={status.running} className="tile-running" />
        <StatusTile label="Success" value={status.success} className="tile-success" />
        <StatusTile label="Failed" value={status.failed} className="tile-failed" />
        <StatusTile label="Queued" value={status.queued} className="tile-queued" />
        <StatusTile label="Total" value={status.total} className="tile-total" />
      </div>

      {status.running_task_run_ids.length > 0 && (
        <div className="running-preview-links">
          <span className="muted">Watch live: </span>
          {status.running_task_run_ids.map((id) => (
            <button key={id} type="button" className="link-button" onClick={() => onPreview(id)}>
              {id.slice(0, 8)}…
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function StatusTile({ label, value, className }: { label: string; value: number; className: string }) {
  return (
    <div className={`status-tile ${className}`}>
      <div className="status-value">{value}</div>
      <div className="status-label">{label}</div>
    </div>
  );
}
