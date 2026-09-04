import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { Target } from "../types";
import { Card, CardTitle } from "./ui/Card";

export function TaskCreateForm({
  targets,
  defaultTargetId,
  onCreated,
}: {
  targets: Target[];
  defaultTargetId?: string;
  onCreated: () => void;
}) {
  const [targetId, setTargetId] = useState(defaultTargetId ?? targets[0]?.id ?? "");
  const [taskType, setTaskType] = useState("performance_check");
  const [cron, setCron] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!targetId) {
      toast.error("Add a target first");
      return;
    }
    setBusy(true);
    try {
      await api.createTask({ target_id: targetId, task_type: taskType, schedule_cron: cron || null });
      setCron("");
      toast.success("Task created");
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardTitle subtitle="Cron is optional — leave it blank for a manually-triggered task.">Create New Task</CardTitle>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Target</label>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {targets.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Task Type</label>
          <select
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="performance_check">performance_check</option>
            <option value="competitor_analysis">competitor_analysis</option>
            <option value="ux_simulation">ux_simulation</option>
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Cron Schedule (optional)</label>
          <input
            placeholder='e.g. "* * * * *"'
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy || !targetId}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? "Creating..." : "Create Task"}
          </button>
        </div>
      </form>
    </Card>
  );
}
