import { CheckCircle2, Clock, Layers, Loader2, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { statusWebSocketUrl } from "../api";
import type { StatusSnapshot } from "../types";

const EMPTY: StatusSnapshot = { queued: 0, running: 0, success: 0, failed: 0, total: 0, running_task_run_ids: [] };

const CARDS = [
  { key: "running" as const, label: "Running", icon: Loader2, classes: "bg-blue-50 text-blue-700 ring-blue-200" },
  { key: "success" as const, label: "Success", icon: CheckCircle2, classes: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  { key: "failed" as const, label: "Failed", icon: XCircle, classes: "bg-red-50 text-red-700 ring-red-200" },
  { key: "queued" as const, label: "Queued", icon: Clock, classes: "bg-amber-50 text-amber-700 ring-amber-200" },
  { key: "total" as const, label: "Total", icon: Layers, classes: "bg-slate-100 text-slate-700 ring-slate-200" },
];

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
        retryTimer = window.setTimeout(connect, 2000);
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
    <div>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-lg font-semibold text-slate-900">Live Visitor Status</h2>
        <span
          className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-red-500"}`}
          title={connected ? "Connected" : "Disconnected"}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {CARDS.map(({ key, label, icon: Icon, classes }) => (
          <div
            key={key}
            className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md`}
          >
            <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md ring-1 ${classes}`}>
              <Icon size={18} className={key === "running" ? "animate-spin" : ""} />
            </div>
            <div className="text-3xl font-bold text-slate-900">{status[key]}</div>
            <div className="text-sm text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {status.running_task_run_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Watch live:</span>
          {status.running_task_run_ids.map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => onPreview(id)}
              className="rounded-md bg-blue-50 px-2 py-1 font-mono text-xs text-blue-700 hover:bg-blue-100"
            >
              {id.slice(0, 8)}…
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
