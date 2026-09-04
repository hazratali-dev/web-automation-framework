import { RuntimeConfigPanel } from "../components/RuntimeConfigPanel";

export function ConfigPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Configuration</h1>
        <p className="text-sm text-slate-500">System-wide runtime settings, applied dynamically.</p>
      </div>
      <RuntimeConfigPanel />
    </div>
  );
}
