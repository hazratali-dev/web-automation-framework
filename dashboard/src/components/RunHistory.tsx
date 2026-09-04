import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { TaskRun } from "../types";
import { Badge, statusVariant } from "./ui/Badge";

export function RunHistory({ taskId }: { taskId: string }) {
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      setRuns(await api.listTaskRuns(taskId));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 4000);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  if (loading) return <p className="p-4 text-sm text-slate-500">Loading…</p>;
  if (runs.length === 0) return <p className="p-4 text-sm text-slate-500">No runs yet.</p>;

  return (
    <div className="overflow-x-auto bg-slate-50 p-3">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left uppercase tracking-wide text-slate-400">
            <th className="py-1.5 pr-3">Status</th>
            <th className="py-1.5 pr-3">Started</th>
            <th className="py-1.5 pr-3">Duration</th>
            <th className="py-1.5 pr-3">Retries</th>
            <th className="py-1.5 pr-3">Metrics / Error</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-t border-slate-200">
              <td className="py-1.5 pr-3">
                <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
              </td>
              <td className="py-1.5 pr-3 text-slate-500">
                {run.started_at ? new Date(run.started_at).toLocaleTimeString() : "—"}
              </td>
              <td className="py-1.5 pr-3 text-slate-500">{run.duration_ms != null ? `${run.duration_ms}ms` : "—"}</td>
              <td className="py-1.5 pr-3 text-slate-500">{run.retry_count}</td>
              <td className="max-w-xs truncate py-1.5 pr-3 text-slate-500">
                {run.error_message
                  ? run.error_message
                  : run.result
                    ? Object.entries(run.result)
                        .filter(([, v]) => v != null)
                        .map(([k, v]) => `${k}=${Math.round(v as number)}`)
                        .join(", ")
                    : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
