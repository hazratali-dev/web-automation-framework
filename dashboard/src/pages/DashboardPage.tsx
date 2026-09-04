import { useState } from "react";
import { LivePreview } from "../components/LivePreview";
import { LiveStatus } from "../components/LiveStatus";
import { RecentRuns } from "../components/RecentRuns";

export function DashboardPage() {
  const [previewTaskRunId, setPreviewTaskRunId] = useState<string | null>(null);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Real-time overview of every automated browser session.</p>
      </div>

      <LiveStatus onPreview={setPreviewTaskRunId} />
      <RecentRuns />

      {previewTaskRunId && (
        <LivePreview taskRunId={previewTaskRunId} onClose={() => setPreviewTaskRunId(null)} />
      )}
    </div>
  );
}
