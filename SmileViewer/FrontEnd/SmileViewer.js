import React, { useMemo, useRef, useEffect } from "react";
import useDataSocket from "./hooks/useDataSocket";
import useVideoSocket from "./hooks/useVideoSocket";
import ControlsPanel from "./components/ControlsPanel";

export default function SmileViewer({ wsUrl, onRecordChange }) {
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

  // Sync recording state with App component
  useEffect(() => {
    if (onRecordChange) {
      onRecordChange(settings.RECORD);
    }
  }, [settings.RECORD, onRecordChange]);

  // eslint-disable-next-line no-unused-vars
  const _facesTick = facesTick; // keep tick referenced to ensure panel updates when faces change

  return (
    <div style={{display:"flex", gap:20}}>
      <div style={{position:"relative", width: "1080px", height: "720px"}}>
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
          facesRef={facesRef}
        />
      </div>
    </div>
  );
}
