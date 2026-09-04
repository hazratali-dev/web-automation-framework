import { ProxyList } from "../components/ProxyList";

export function ProxiesPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Proxies</h1>
        <p className="text-sm text-slate-500">Pool health, rotation stats, and success rates.</p>
      </div>
      <ProxyList />
    </div>
  );
}
