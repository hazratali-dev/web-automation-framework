import { useEffect, useState } from "react";
import { api } from "../api";
import type { RuntimeConfigItem } from "../types";

export function RuntimeConfigPanel() {
  const [items, setItems] = useState<RuntimeConfigItem[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function refresh() {
    setItems(await api.listConfig());
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleChange(key: string, value: string) {
    setBusyKey(key);
    try {
      await api.updateConfig(key, value);
      await refresh();
    } finally {
      setBusyKey(null);
    }
  }

  const concurrency = items.find((i) => i.key === "max_concurrent_browsers");
  const strategy = items.find((i) => i.key === "proxy_strategy");
  const timeout = items.find((i) => i.key === "default_timeout_seconds");
  const headless = items.find((i) => i.key === "headless");

  return (
    <section className="panel">
      <h2>Runtime Configuration</h2>
      <p className="muted">Takes effect on the next batch/selection, no restart needed (§5.6).</p>
      <div className="config-row">
        <label>
          max_concurrent_browsers
          <input
            type="number"
            min={1}
            max={50}
            defaultValue={concurrency?.value ?? "5"}
            disabled={busyKey === "max_concurrent_browsers"}
            onBlur={(e) => handleChange("max_concurrent_browsers", e.target.value)}
          />
        </label>
        <label>
          proxy_strategy
          <select
            defaultValue={strategy?.value ?? "round_robin"}
            disabled={busyKey === "proxy_strategy"}
            onChange={(e) => handleChange("proxy_strategy", e.target.value)}
          >
            <option value="round_robin">round_robin</option>
            <option value="weighted">weighted</option>
          </select>
        </label>
        <label>
          default_timeout_seconds
          <input
            type="number"
            min={5}
            max={120}
            defaultValue={timeout?.value ?? "30"}
            disabled={busyKey === "default_timeout_seconds"}
            onBlur={(e) => handleChange("default_timeout_seconds", e.target.value)}
          />
        </label>
        <label>
          headless (browser window)
          <select
            key={headless?.value ?? "false"}
            defaultValue={headless?.value ?? "false"}
            disabled={busyKey === "headless"}
            onChange={(e) => handleChange("headless", e.target.value)}
          >
            <option value="false">false — window visible</option>
            <option value="true">true — hidden</option>
          </select>
        </label>
      </div>
      <p className="muted small">
        Changing headless restarts the browser process — it applies as soon as no session is currently running.
      </p>
    </section>
  );
}
