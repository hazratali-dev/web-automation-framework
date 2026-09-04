import type { Proxy, RuntimeConfigItem, Target, Task, TaskRun } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  listTargets: () => request<Target[]>("/api/targets"),
  createTarget: (body: { name: string; base_url: string; target_type: string }) =>
    request<Target>("/api/targets", { method: "POST", body: JSON.stringify(body) }),
  setCredentials: (targetId: string, email: string, password: string) =>
    request<void>(`/api/targets/${targetId}/credentials`, {
      method: "PATCH",
      body: JSON.stringify({ email, password }),
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

  listProxies: () => request<Proxy[]>("/api/proxies"),

  listConfig: () => request<RuntimeConfigItem[]>("/api/config"),
  updateConfig: (key: string, value: string) =>
    request<RuntimeConfigItem>(`/api/config/${key}`, { method: "PATCH", body: JSON.stringify({ value }) }),
};

export function statusWebSocketUrl(): string {
  const wsBase = BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/ws/status`;
}
