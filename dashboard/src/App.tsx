import { useState } from "react";
import "./App.css";
import { LivePreview } from "./components/LivePreview";
import { LiveStatus } from "./components/LiveStatus";
import { ProxyList } from "./components/ProxyList";
import { RuntimeConfigPanel } from "./components/RuntimeConfigPanel";
import { TargetForm } from "./components/TargetForm";
import { TargetList } from "./components/TargetList";

function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [previewTaskRunId, setPreviewTaskRunId] = useState<string | null>(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Web Automation Framework — Dashboard</h1>
        <p className="muted">Phase 5 · SQLite + asyncio, single uvicorn process</p>
      </header>

      <LiveStatus onPreview={setPreviewTaskRunId} />
      <TargetForm onCreated={() => setRefreshKey((k) => k + 1)} />
      <TargetList refreshKey={refreshKey} />
      <RuntimeConfigPanel />
      <ProxyList />

      {previewTaskRunId && (
        <LivePreview taskRunId={previewTaskRunId} onClose={() => setPreviewTaskRunId(null)} />
      )}
    </div>
  );
}

export default App;
