import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { TaskCreateForm } from "../components/TaskCreateForm";
import { TasksTable } from "../components/TasksTable";
import type { Target, Task } from "../types";

export function TasksPage() {
  const [searchParams] = useSearchParams();
  const targetIdFilter = searchParams.get("target_id") ?? undefined;

  const [targets, setTargets] = useState<Target[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);

  async function refresh() {
    try {
      const [targetsRes, tasksRes] = await Promise.all([api.listTargets(), api.listTasks(targetIdFilter)]);
      setTargets(targetsRes);
      setTasks(tasksRes);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetIdFilter]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Tasks</h1>
        <p className="text-sm text-slate-500">
          {targetIdFilter
            ? `Showing tasks for ${targets.find((t) => t.id === targetIdFilter)?.name ?? "this target"}`
            : "Every scheduled or manually-triggered task, across all targets."}
        </p>
      </div>

      {targets.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
          Add a target first (Targets page) before creating tasks.
        </p>
      ) : (
        <TaskCreateForm targets={targets} defaultTargetId={targetIdFilter} onCreated={refresh} />
      )}

      <TasksTable tasks={tasks} targets={targets} onChanged={refresh} />
    </div>
  );
}
