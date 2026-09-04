import { ChevronDown, ChevronRight, Pause, Play, Users } from "lucide-react";
import { Fragment, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { Target, Task } from "../types";
import { Badge, statusVariant } from "./ui/Badge";
import { Card, CardTitle } from "./ui/Card";
import { RunHistory } from "./RunHistory";

export function TasksTable({
  tasks,
  targets,
  onChanged,
}: {
  tasks: Task[];
  targets: Target[];
  onChanged: () => void;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [visitorCounts, setVisitorCounts] = useState<Record<string, number>>({});

  const targetName = (id: string) => targets.find((t) => t.id === id)?.name ?? "—";

  async function handleToggleStatus(task: Task) {
    setBusyId(task.id);
    try {
      await api.setTaskStatus(task.id, task.status === "active" ? "paused" : "active");
      onChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function handleRunNow(task: Task) {
    setBusyId(task.id);
    try {
      await api.runNow(task.id);
      toast.success(`Task started — watch it on the Dashboard`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function handleSimulateVisitors(task: Task) {
    const count = visitorCounts[task.id] ?? 10;
    setBusyId(task.id);
    try {
      await api.simulateVisitors(task.id, count);
      toast.success(`${count} visitor simulation started — watch it on the Dashboard`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Card>
      <CardTitle>Tasks</CardTitle>

      {tasks.length === 0 ? (
        <p className="text-sm text-slate-500">No tasks yet — create one above.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4"></th>
                <th className="py-2 pr-4">Target</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Schedule</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <Fragment key={task.id}>
                  <tr className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 pl-1">
                      <button
                        type="button"
                        onClick={() => setExpandedId(expandedId === task.id ? null : task.id)}
                        className="text-slate-400 hover:text-slate-700"
                      >
                        {expandedId === task.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                    </td>
                    <td className="py-3 pr-4 font-medium text-slate-800">{targetName(task.target_id)}</td>
                    <td className="py-3 pr-4 text-slate-600">{task.task_type}</td>
                    <td className="py-3 pr-4">
                      {task.schedule_cron ? (
                        <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{task.schedule_cron}</code>
                      ) : (
                        <span className="text-slate-400">manual</span>
                      )}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant={statusVariant(task.status)}>{task.status}</Badge>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          title="Run Now"
                          onClick={() => handleRunNow(task)}
                          disabled={busyId === task.id || task.status !== "active"}
                          className="rounded-md p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-40"
                        >
                          <Play size={16} />
                        </button>
                        <button
                          type="button"
                          title={task.status === "active" ? "Pause" : "Resume"}
                          onClick={() => handleToggleStatus(task)}
                          disabled={busyId === task.id}
                          className="rounded-md p-2 text-slate-500 hover:bg-amber-50 hover:text-amber-600 disabled:opacity-40"
                        >
                          {task.status === "active" ? <Pause size={16} /> : <Play size={16} />}
                        </button>
                        <input
                          type="number"
                          min={1}
                          max={200}
                          value={visitorCounts[task.id] ?? 10}
                          onChange={(e) =>
                            setVisitorCounts((prev) => ({ ...prev, [task.id]: Number(e.target.value) }))
                          }
                          className="w-14 rounded-md border border-slate-300 px-1.5 py-1 text-xs"
                        />
                        <button
                          type="button"
                          title="Simulate Visitors"
                          onClick={() => handleSimulateVisitors(task)}
                          disabled={busyId === task.id || task.status !== "active"}
                          className="flex items-center gap-1 rounded-md bg-blue-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-40"
                        >
                          <Users size={14} /> Simulate
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === task.id && (
                    <tr>
                      <td colSpan={6} className="p-0">
                        <RunHistory taskId={task.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
