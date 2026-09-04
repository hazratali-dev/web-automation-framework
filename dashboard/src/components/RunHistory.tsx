import { useEffect, useState } from "react";
import { api } from "../api";
import type { TaskRun } from "../types";

export function RunHistory({ taskId }: { taskId: string }) {
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    if (!open) {
      setLoading(true);
      try {
        setRuns(await api.listTaskRuns(taskId));
      } finally {
        setLoading(false);
      }
    }
    setOpen((o) => !o);
  }

  // Keep it fresh while open, in case a run finishes while the user is looking.
  useEffect(() => {
    if (!open) return;
    const interval = window.setInterval(() => {
      api.listTaskRuns(taskId).then(setRuns);
    }, 4000);
    return () => window.clearInterval(interval);
  }, [open, taskId]);

  return (
    <div className="run-history">
      <button type="button" className="link-button" onClick={toggle}>
        {open ? "Hide Run History" : "Show Run History"}
      </button>

      {open && (
        <>
          {loading && <p className="muted">Loading…</p>}
          {!loading && runs.length === 0 && <p className="muted">No runs yet.</p>}
          {!loading && runs.length > 0 && (
            <table className="run-history-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Retries</th>
                  <th>Metrics / Error</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <span className={`badge badge-run-${run.status}`}>{run.status}</span>
                    </td>
                    <td>{run.started_at ? new Date(run.started_at).toLocaleTimeString() : "—"}</td>
                    <td>{run.duration_ms != null ? `${run.duration_ms}ms` : "—"}</td>
                    <td>{run.retry_count}</td>
                    <td className="run-history-detail">
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
          )}
        </>
      )}
    </div>
  );
}
