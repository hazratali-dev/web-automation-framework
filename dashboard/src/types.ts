export type LoginType = "email_password" | "single_password";

export interface Target {
  id: string;
  name: string;
  base_url: string;
  target_type: string;
  is_active: boolean;
  has_credentials: boolean;
  created_at: string | null;
}

export type TaskStatus = "active" | "paused" | "archived";

export interface Task {
  id: string;
  target_id: string;
  task_type: string;
  schedule_cron: string | null;
  priority: number;
  status: TaskStatus;
  created_at: string | null;
}

export interface TaskRun {
  id: string;
  task_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  retry_count: number;
  error_message: string | null;
  result: Record<string, number | null> | null;
  screenshot_path: string | null;
}

export interface Proxy {
  id: string;
  host: string;
  port: number;
  protocol: string;
  provider: string | null;
  country: string | null;
  is_active: boolean;
  consecutive_failures: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_latency_ms: number | null;
}

export interface RuntimeConfigItem {
  key: string;
  value: string;
}

export interface StatusSnapshot {
  queued: number;
  running: number;
  success: number;
  failed: number;
  total: number;
  running_task_run_ids: string[];
}

export interface PreviewFrame {
  active: boolean;
  image?: string;
}
