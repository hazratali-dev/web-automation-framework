import { useState } from "react";
import { api } from "../api";
import type { LoginType, Target } from "../types";

export function CredentialsForm({ target, onChanged }: { target: Target; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [loginType, setLoginType] = useState<LoginType>("email_password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.setCredentials(target.id, loginType === "single_password" ? null : email, password, loginType);
      setEmail("");
      setPassword("");
      setOpen(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteCredentials(target.id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="credentials-block">
      <span className={`badge ${target.has_credentials ? "badge-ok" : "badge-muted"}`}>
        {target.has_credentials ? "ক্রেডেনশিয়াল সেট করা আছে" : "কোনো ক্রেডেনশিয়াল নেই"}
      </span>
      <button type="button" className="link-button" onClick={() => setOpen((o) => !o)}>
        {open ? "বাতিল" : target.has_credentials ? "পরিবর্তন করুন" : "সেট করুন"}
      </button>
      {target.has_credentials && (
        <button type="button" className="link-button link-danger" onClick={handleDelete} disabled={busy}>
          মুছে ফেলুন
        </button>
      )}

      {open && (
        <form onSubmit={handleSave} className="form-row form-row-compact">
          <select value={loginType} onChange={(e) => setLoginType(e.target.value as LoginType)}>
            <option value="email_password">Email + Password</option>
            <option value="single_password">Single Password (Shopify/cPanel)</option>
          </select>
          {loginType === "email_password" && (
            <input
              placeholder="Login email/username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          )}
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={busy}>
            Save
          </button>
        </form>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
