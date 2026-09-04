import { useEffect, useRef, useState } from "react";
import { previewWebSocketUrl } from "../api";

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
    <div className="live-preview-overlay" onClick={onClose}>
      <div className="live-preview-panel" onClick={(e) => e.stopPropagation()}>
        <div className="live-preview-header">
          <strong>Live Preview</strong>
          <span className="muted"> — {taskRunId.slice(0, 8)}… (updates every ~3s)</span>
          <button type="button" className="link-button" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="live-preview-body">
          {image ? (
            <img src={image} alt="Live browser preview" className="live-preview-image" />
          ) : (
            <p className="muted">Waiting for the first frame…</p>
          )}
          {!active && <p className="hint">This session has finished — showing its last frame.</p>}
        </div>
      </div>
    </div>
  );
}
