import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api";
import type { LoginType, Target } from "../types";
import { Modal } from "./ui/Modal";

export function CredentialsModal({ target, onClose, onChanged }: { target: Target; onClose: () => void; onChanged: () => void }) {
  const [loginType, setLoginType] = useState<LoginType>("email_password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.setCredentials(target.id, loginType === "single_password" ? null : email, password, loginType);
      toast.success("Credentials saved");
      onChanged();
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    try {
      await api.deleteCredentials(target.id);
      toast.success("Credentials removed");
      onChanged();
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={`Credentials — ${target.name}`} onClose={onClose}>
      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Login Type</label>
          <select
            value={loginType}
            onChange={(e) => setLoginType(e.target.value as LoginType)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="email_password">Email + Password</option>
            <option value="single_password">Single Password (Shopify/cPanel)</option>
          </select>
        </div>

        {loginType === "email_password" && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Email / Username</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center justify-between pt-2">
          {target.has_credentials ? (
            <button
              type="button"
              onClick={handleDelete}
              disabled={busy}
              className="text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
            >
              Remove Credentials
            </button>
          ) : (
            <span />
          )}
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </form>
    </Modal>
  );
}
