import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { RuntimeConfigItem } from "../types";
import { Card, CardTitle } from "./ui/Card";
import { ToggleSwitch } from "./ui/ToggleSwitch";

export function RuntimeConfigPanel() {
  const [items, setItems] = useState<RuntimeConfigItem[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function refresh() {
    try {
      setItems(await api.listConfig());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleChange(key: string, value: string, successMessage?: string) {
    setBusyKey(key);
    try {
      await api.updateConfig(key, value);
      if (successMessage) toast.success(successMessage);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyKey(null);
    }
  }

  const concurrency = items.find((i) => i.key === "max_concurrent_browsers");
  const strategy = items.find((i) => i.key === "proxy_strategy");
  const timeout = items.find((i) => i.key === "default_timeout_seconds");
  const headless = items.find((i) => i.key === "headless");
  const isHeadless = headless?.value === "true";

  return (
    <Card>
      <CardTitle subtitle="Takes effect on the next batch/selection — no restart needed (§5.6).">
        Runtime Configuration
      </CardTitle>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">max_concurrent_browsers</label>
          <input
            type="number"
            min={1}
            max={50}
            defaultValue={concurrency?.value ?? "5"}
            disabled={busyKey === "max_concurrent_browsers"}
            onBlur={(e) => handleChange("max_concurrent_browsers", e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">proxy_strategy</label>
          <select
            defaultValue={strategy?.value ?? "round_robin"}
            disabled={busyKey === "proxy_strategy"}
            onChange={(e) => handleChange("proxy_strategy", e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="round_robin">round_robin</option>
            <option value="weighted">weighted</option>
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">default_timeout_seconds</label>
          <input
            type="number"
            min={5}
            max={120}
            defaultValue={timeout?.value ?? "30"}
            disabled={busyKey === "default_timeout_seconds"}
            onBlur={(e) => handleChange("default_timeout_seconds", e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Headless Mode</label>
          <div className="flex items-center gap-3 pt-1">
            <ToggleSwitch
              checked={isHeadless}
              disabled={busyKey === "headless"}
              onChange={(checked) =>
                handleChange(
                  "headless",
                  checked ? "true" : "false",
                  checked
                    ? "Headless enabled — browser window will be hidden"
                    : "Headless disabled — browser window will be visible"
                )
              }
            />
            <span className="text-sm text-slate-600">
              Browser Window: <strong>{isHeadless ? "Hidden" : "Visible"}</strong>
            </span>
          </div>
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-400">
        Changing headless restarts the browser process — it applies as soon as no session is currently running.
      </p>
    </Card>
  );
}
