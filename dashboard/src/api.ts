import type { LoginType, Proxy, RecentRun, RuntimeConfigItem, Target, Task, TaskRun } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error(`Could not reach the API at ${BASE_URL} — is the backend running?`);
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      if (typeof parsed?.detail === "string") detail = parsed.detail;
      else if (Array.isArray(parsed?.detail)) detail = parsed.detail.map((d: { msg?: string }) => d.msg).join(", ");
    } catch {
      // body wasn't JSON — use the raw text as-is
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  listTargets: () => request<Target[]>("/api/targets"),
  createTarget: (body: { name: string; base_url: string; target_type: string }) =>
    request<Target>("/api/targets", { method: "POST", body: JSON.stringify(body) }),
  updateTarget: (targetId: string, body: { name?: string; base_url?: string; target_type?: string }) =>
    request<Target>(`/api/targets/${targetId}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTarget: (targetId: string) => request<void>(`/api/targets/${targetId}`, { method: "DELETE" }),
  setCredentials: (targetId: string, email: string | null, password: string, loginType: LoginType) =>
    request<void>(`/api/targets/${targetId}/credentials`, {
      method: "PATCH",
      body: JSON.stringify({ email, password, login_type: loginType }),
    }),
  deleteCredentials: (targetId: string) =>
    request<void>(`/api/targets/${targetId}/credentials`, { method: "DELETE" }),

  listTasks: (targetId?: string) =>
    request<Task[]>(`/api/tasks${targetId ? `?target_id=${targetId}` : ""}`),
  createTask: (body: { target_id: string; task_type: string; schedule_cron?: string | null }) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(body) }),
  setTaskStatus: (taskId: string, status: string) =>
    request<Task>(`/api/tasks/${taskId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  runNow: (taskId: string) => request<{ submitted: boolean }>(`/api/tasks/${taskId}/run-now`, { method: "POST" }),
  simulateVisitors: (taskId: string, count: number) =>
    request<{ started: boolean; count: number }>(`/api/tasks/${taskId}/simulate-visitors?count=${count}`, {
      method: "POST",
    }),
  listTaskRuns: (taskId: string) => request<TaskRun[]>(`/api/tasks/${taskId}/runs`),
  listRecentRuns: (limit = 20) => request<RecentRun[]>(`/api/task-runs/recent?limit=${limit}`),

  listProxies: () => request<Proxy[]>("/api/proxies"),

  listConfig: () => request<RuntimeConfigItem[]>("/api/config"),
  updateConfig: (key: string, value: string) =>
    request<RuntimeConfigItem>(`/api/config/${key}`, { method: "PATCH", body: JSON.stringify({ value }) }),
};

export function statusWebSocketUrl(): string {
  const wsBase = BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/ws/status`;
}

export function previewWebSocketUrl(taskRunId: string): string {
  const wsBase = BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/ws/preview/${taskRunId}`;
}
