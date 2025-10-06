import React, { useMemo, useRef } from "react";
import useDataSocket from "./hooks/useDataSocket";
import useVideoSocket from "./hooks/useVideoSocket";
import ControlsPanel from "./components/ControlsPanel";

export default function SmileViewer({ wsUrl }) {
  const videoCanvasRef = useRef(null);

  const resolvedWsUrl = useMemo(() => {
    if (wsUrl) return wsUrl;
    const isSecure = window.location.protocol === "https:";
    const wsProto = isSecure ? "wss" : "ws";
    const host = window.location.hostname || "localhost";
    const port = 8000;
    return `${wsProto}://${host}:${port}/controls`;
  }, [wsUrl]);

  const {
    ws,
    connected,
    facesRef,
    facesTick, // eslint-guard for potential re-render triggers
    settings,
    setSettings,
    sendStateToServer,
  } = useDataSocket(resolvedWsUrl);

  const { videoWs, videoConnected } = useVideoSocket(resolvedWsUrl, videoCanvasRef);

  // eslint-disable-next-line no-unused-vars
  const _facesTick = facesTick; // keep tick referenced to ensure panel updates when faces change

  return (
    <div style={{display:"flex", gap:20}}>
      <div style={{position:"relative", width: "640px", height: "480px"}}>
        <canvas
          ref={videoCanvasRef}
          style={{ width: "100%", height: "100%", objectFit: "contain", display: "block", border: "1px solid #ccc" }}
        />
      </div>

      <div style={{minWidth: 260}}>
        <ControlsPanel
          settings={settings}
          setSettings={setSettings}
          sendStateToServer={sendStateToServer}
          connections={{
            dataConnected: connected,
            videoConnected: videoConnected,
            facesCount: facesRef.current.length,
          }}
        />
        <hr/>
        <div>
          <h4>Faces</h4>
          {facesRef.current.length === 0 ? (
            <div>No faces</div>
          ) : (
            facesRef.current.map(f => (
              <div key={f.face_id} style={{marginBottom:8}}>
                <strong>Face {f.face_id}</strong><br/>
                Face bbox: {f.face_bbox ? f.face_bbox.join(",") : "-1,-1,-1,-1"}<br/>
                Smile bbox: {f.smile_status == 'Smiling' ? f.smile_bbox.join(",") : "-1,-1,-1,-1"}<br/>
                Status: {f.smile_status}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
