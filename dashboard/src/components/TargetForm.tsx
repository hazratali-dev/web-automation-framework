import { useState } from "react";
import { api } from "../api";

export function TargetForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [targetType, setTargetType] = useState("own_site");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createTarget({ name, base_url: baseUrl, target_type: targetType });
      setName("");
      setBaseUrl("");
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Add New Target</h2>
      <form onSubmit={handleSubmit} className="form-row">
        <input
          placeholder="Name (e.g. My Website)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          placeholder="https://example.com"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          required
          type="url"
        />
        <select value={targetType} onChange={(e) => setTargetType(e.target.value)}>
          <option value="own_site">own_site</option>
          <option value="competitor">competitor</option>
        </select>
        <button type="submit" disabled={busy}>
          {busy ? "Adding..." : "Add Target"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
