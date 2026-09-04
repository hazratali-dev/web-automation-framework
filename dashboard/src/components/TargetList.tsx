import { useEffect, useState } from "react";
import { api } from "../api";
import type { Target } from "../types";
import { CredentialsForm } from "./CredentialsForm";
import { TaskPanel } from "./TaskPanel";

export function TargetList({ refreshKey }: { refreshKey: number }) {
  const [targets, setTargets] = useState<Target[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function refresh() {
    setTargets(await api.listTargets());
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  return (
    <section className="panel">
      <h2>Targets</h2>
      {targets.length === 0 && <p className="muted">No targets added yet.</p>}
      <ul className="target-list">
        {targets.map((target) => (
          <li key={target.id} className="target-card">
            <div className="target-header" onClick={() => setExpandedId(expandedId === target.id ? null : target.id)}>
              <div>
                <strong>{target.name}</strong>
                <span className="muted"> — {target.base_url}</span>
              </div>
              <span className={`badge ${target.is_active ? "badge-ok" : "badge-muted"}`}>{target.target_type}</span>
            </div>

            <CredentialsForm target={target} onChanged={refresh} />

            {expandedId === target.id ? (
              <TaskPanel target={target} />
            ) : (
              <button type="button" className="link-button" onClick={() => setExpandedId(target.id)}>
                View / Add Tasks
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
