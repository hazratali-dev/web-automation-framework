import { useEffect, useRef, useState } from "react";
import { previewWebSocketUrl } from "../api";
import { Modal } from "./ui/Modal";

export function LivePreview({ taskRunId, onClose }: { taskRunId: string; onClose: () => void }) {
  const [image, setImage] = useState<string | null>(null);
  const [active, setActive] = useState(true);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(previewWebSocketUrl(taskRunId));
    socketRef.current = ws;

    ws.onmessage = (event) => {
      const frame = JSON.parse(event.data) as { active: boolean; image?: string };
      setActive(frame.active);
      if (frame.image) setImage(frame.image);
    };

    return () => ws.close();
  }, [taskRunId]);

  return (
    <Modal title={`Live Preview — ${taskRunId.slice(0, 8)}… (updates every ~3s)`} onClose={onClose} wide>
      {image ? (
        <img src={image} alt="Live browser preview" className="w-full rounded-md border border-slate-200" />
      ) : (
        <p className="py-12 text-center text-sm text-slate-500">Waiting for the first frame…</p>
      )}
      {!active && (
        <p className="mt-3 text-sm text-emerald-600">This session has finished — showing its last frame.</p>
      )}
    </Modal>
  );
}
