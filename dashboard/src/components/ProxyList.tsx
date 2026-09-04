import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { Proxy } from "../types";
import { Badge } from "./ui/Badge";
import { Card, CardTitle } from "./ui/Card";

export function ProxyList() {
  const [proxies, setProxies] = useState<Proxy[]>([]);

  useEffect(() => {
    api
      .listProxies()
      .then(setProxies)
      .catch((err) => toast.error(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <Card>
      <CardTitle subtitle="Managed via the Phase 2 CLI — rotation strategy is set on the Config page.">
        Proxy Pool
      </CardTitle>

      {proxies.length === 0 ? (
        <p className="text-sm text-slate-500">No proxies added yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Host</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Success Rate</th>
                <th className="py-2 pr-4">Consecutive Fails</th>
                <th className="py-2 pr-4">Latency</th>
              </tr>
            </thead>
            <tbody>
              {proxies.map((p) => (
                <tr key={p.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-4 font-mono text-xs text-slate-700">
                    {p.protocol}://{p.host}:{p.port}
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={p.is_active ? "ok" : "muted"}>{p.is_active ? "active" : "inactive"}</Badge>
                  </td>
                  <td className="py-2 pr-4 text-slate-600">{(p.success_rate * 100).toFixed(0)}%</td>
                  <td className="py-2 pr-4 text-slate-600">{p.consecutive_failures}</td>
                  <td className="py-2 pr-4 text-slate-600">{p.avg_latency_ms != null ? `${p.avg_latency_ms}ms` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
