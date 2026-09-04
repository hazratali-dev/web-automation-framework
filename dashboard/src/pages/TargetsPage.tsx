import { useState } from "react";
import { AddTargetForm } from "../components/AddTargetForm";
import { TargetsTable } from "../components/TargetsTable";

export function TargetsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Targets</h1>
        <p className="text-sm text-slate-500">Sites to monitor, analyze, or simulate visitors on.</p>
      </div>

      <AddTargetForm onCreated={bump} />
      <TargetsTable refreshKey={refreshKey} onChanged={bump} />
    </div>
  );
}
