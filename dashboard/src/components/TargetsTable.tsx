import { KeyRound, Pencil, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Target } from "../types";
import { Badge } from "./ui/Badge";
import { Card, CardTitle } from "./ui/Card";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { CredentialsModal } from "./CredentialsModal";
import { EditTargetModal } from "./EditTargetModal";

export function TargetsTable({ refreshKey, onChanged }: { refreshKey: number; onChanged: () => void }) {
  const [targets, setTargets] = useState<Target[]>([]);
  const [editTarget, setEditTarget] = useState<Target | null>(null);
  const [credentialsTarget, setCredentialsTarget] = useState<Target | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Target | null>(null);

  async function refresh() {
    try {
      setTargets(await api.listTargets());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await api.deleteTarget(deleteTarget.id);
      toast.success(`Target "${deleteTarget.name}" deleted`);
      setDeleteTarget(null);
      refresh();
      onChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
      setDeleteTarget(null);
    }
  }

  return (
    <Card>
      <CardTitle>Targets</CardTitle>

      {targets.length === 0 ? (
        <p className="text-sm text-slate-500">No targets added yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">URL</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Credentials</th>
                <th className="py-2 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {targets.map((target) => (
                <tr key={target.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="py-3 pr-4 font-medium text-slate-800">
                    <Link to={`/tasks?target_id=${target.id}`} className="hover:text-blue-600 hover:underline">
                      {target.name}
                    </Link>
                  </td>
                  <td className="py-3 pr-4 max-w-xs truncate text-slate-500">{target.base_url}</td>
                  <td className="py-3 pr-4">
                    <Badge variant={target.target_type === "own_site" ? "info" : "muted"}>{target.target_type}</Badge>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant={target.has_credentials ? "ok" : "muted"}>
                      {target.has_credentials ? "Set" : "Not Set"}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        title="Set Credentials"
                        onClick={() => setCredentialsTarget(target)}
                        className="rounded-md p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-600"
                      >
                        <KeyRound size={16} />
                      </button>
                      <button
                        type="button"
                        title="Edit"
                        onClick={() => setEditTarget(target)}
                        className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        title="Delete"
                        onClick={() => setDeleteTarget(target)}
                        className="rounded-md p-2 text-slate-500 hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editTarget && (
        <EditTargetModal target={editTarget} onClose={() => setEditTarget(null)} onChanged={refresh} />
      )}
      {credentialsTarget && (
        <CredentialsModal target={credentialsTarget} onClose={() => setCredentialsTarget(null)} onChanged={refresh} />
      )}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Target"
          message={`Delete "${deleteTarget.name}"? This can't be undone. Targets with existing tasks can't be deleted — remove those tasks first.`}
          confirmLabel="Delete"
          danger
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </Card>
  );
}
