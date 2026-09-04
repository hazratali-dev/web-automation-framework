import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import { Card, CardTitle } from "./ui/Card";

export function AddTargetForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [targetType, setTargetType] = useState("own_site");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.createTarget({ name, base_url: baseUrl, target_type: targetType });
      setName("");
      setBaseUrl("");
      toast.success(`Target "${name}" added`);
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardTitle subtitle="Register a site to monitor, analyze, or simulate visitors on.">Add New Target</CardTitle>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-1">
          <label htmlFor="target-name" className="mb-1.5 block text-sm font-medium text-slate-700">
            Display Name
          </label>
          <input
            id="target-name"
            placeholder="My Website"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="sm:col-span-1 lg:col-span-2">
          <label htmlFor="target-url" className="mb-1.5 block text-sm font-medium text-slate-700">
            Website URL
          </label>
          <input
            id="target-url"
            placeholder="https://example.com"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            required
            type="url"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="sm:col-span-1">
          <label htmlFor="target-type" className="mb-1.5 block text-sm font-medium text-slate-700">
            Type
          </label>
          <select
            id="target-type"
            value={targetType}
            onChange={(e) => setTargetType(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="own_site">own_site</option>
            <option value="competitor">competitor</option>
          </select>
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? "Adding..." : "Add Target"}
          </button>
        </div>
      </form>
    </Card>
  );
}
