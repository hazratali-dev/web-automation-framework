import { useEffect, useState } from "react";
import { api } from "../api";
import type { Proxy } from "../types";

export function ProxyList() {
  const [proxies, setProxies] = useState<Proxy[]>([]);

  useEffect(() => {
    api.listProxies().then(setProxies);
  }, []);

  if (proxies.length === 0) {
    return (
      <section className="panel">
        <h2>প্রক্সি পুল</h2>
        <p className="muted">কোনো প্রক্সি যোগ করা হয়নি (CLI/Phase 2 দিয়ে যোগ করুন)।</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>প্রক্সি পুল</h2>
      <table className="proxy-table">
        <thead>
          <tr>
            <th>Host</th>
            <th>Status</th>
            <th>Success rate</th>
            <th>Fails</th>
            <th>Latency</th>
          </tr>
        </thead>
        <tbody>
          {proxies.map((p) => (
            <tr key={p.id}>
              <td>
                {p.protocol}://{p.host}:{p.port}
              </td>
              <td>
                <span className={`badge ${p.is_active ? "badge-ok" : "badge-muted"}`}>
                  {p.is_active ? "active" : "inactive"}
                </span>
              </td>
              <td>{(p.success_rate * 100).toFixed(0)}%</td>
              <td>{p.consecutive_failures}</td>
              <td>{p.avg_latency_ms != null ? `${p.avg_latency_ms}ms` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
