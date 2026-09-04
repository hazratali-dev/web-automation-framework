import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { RecentRun } from "../types";
import { Badge, statusVariant } from "./ui/Badge";
import { Card, CardTitle } from "./ui/Card";

export function RecentRuns() {
  const [runs, setRuns] = useState<RecentRun[]>([]);

  async function refresh() {
    try {
      setRuns(await api.listRecentRuns(20));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 5000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <Card>
      <CardTitle subtitle="Every task run across all targets, newest first.">Recent Runs</CardTitle>

      {runs.length === 0 ? (
        <p className="text-sm text-slate-500">No runs yet — trigger a task from the Tasks page.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Task</th>
                <th className="py-2 pr-4">Started</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Duration</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-4">
                    <span className="font-medium text-slate-800">{run.target_name}</span>
                    <span className="text-slate-400"> — {run.task_type}</span>
                  </td>
                  <td className="py-2 pr-4 text-slate-500">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                  </td>
                  <td className="py-2 pr-4 text-slate-500">
                    {run.duration_ms != null ? `${run.duration_ms}ms` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
