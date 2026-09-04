import { useEffect, useState } from "react";
import { api } from "../api";
import type { Target, Task } from "../types";

export function TaskPanel({ target }: { target: Target }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskType, setTaskType] = useState("performance_check");
  const [cron, setCron] = useState("");
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [visitorCount, setVisitorCount] = useState(10);

  async function refresh() {
    setTasks(await api.listTasks(target.id));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target.id]);

  async function handleCreateTask(e: React.FormEvent) {
    e.preventDefault();
    await api.createTask({ target_id: target.id, task_type: taskType, schedule_cron: cron || null });
    setCron("");
    await refresh();
  }

  async function handleToggleStatus(task: Task) {
    setBusyTaskId(task.id);
    const next = task.status === "active" ? "paused" : "active";
    try {
      await api.setTaskStatus(task.id, next);
      await refresh();
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleRunNow(task: Task) {
    setBusyTaskId(task.id);
    setMessage(null);
    try {
      await api.runNow(task.id);
      setMessage(`Task ${task.task_type} চালু হয়েছে — লাইভ স্ট্যাটাস প্যানেলে দেখুন।`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleSimulateVisitors(task: Task) {
    setBusyTaskId(task.id);
    setMessage(null);
    try {
      await api.simulateVisitors(task.id, visitorCount);
      setMessage(`${visitorCount} জন ভিজিটর সিমুলেশন শুরু হয়েছে — লাইভ স্ট্যাটাস প্যানেলে দেখুন।`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyTaskId(null);
    }
  }

  return (
    <div className="task-panel">
      <form onSubmit={handleCreateTask} className="form-row form-row-compact">
        <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
          <option value="performance_check">performance_check</option>
          <option value="competitor_analysis">competitor_analysis</option>
          <option value="ux_simulation">ux_simulation</option>
        </select>
        <input
          placeholder='cron (ঐচ্ছিক, যেমন "* * * * *")'
          value={cron}
          onChange={(e) => setCron(e.target.value)}
        />
        <button type="submit">Create Task</button>
      </form>

      {tasks.length === 0 && <p className="muted">এই টার্গেটের জন্য এখনো কোনো টাস্ক নেই।</p>}

      <ul className="task-list">
        {tasks.map((task) => (
          <li key={task.id} className="task-row">
            <span className={`badge badge-status-${task.status}`}>{task.status}</span>
            <span className="task-type">{task.task_type}</span>
            {task.schedule_cron && <code className="cron">{task.schedule_cron}</code>}
            <div className="task-actions">
              <button
                type="button"
                onClick={() => handleRunNow(task)}
                disabled={busyTaskId === task.id || task.status !== "active"}
              >
                Run Now
              </button>
              <button type="button" onClick={() => handleToggleStatus(task)} disabled={busyTaskId === task.id}>
                {task.status === "active" ? "Pause" : "Resume"}
              </button>
              <input
                type="number"
                min={1}
                max={200}
                value={visitorCount}
                onChange={(e) => setVisitorCount(Number(e.target.value))}
                className="visitor-count-input"
              />
              <button
                type="button"
                onClick={() => handleSimulateVisitors(task)}
                disabled={busyTaskId === task.id || task.status !== "active"}
              >
                Simulate Visitors
              </button>
            </div>
          </li>
        ))}
      </ul>
      {message && <p className="hint">{message}</p>}
    </div>
  );
}
