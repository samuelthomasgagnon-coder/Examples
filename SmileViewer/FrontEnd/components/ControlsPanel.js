import React from "react";

export default function ControlsPanel({ settings, setSettings, sendStateToServer, connections, facesRef }) {
  const { DRAW_LANDMARKS, DRAW_FACE_BB, DRAW_SMILE_BB, DRAW_ROTATED_BB, RECORD, TEST_MODE } = settings;
  const { dataConnected, videoConnected, facesCount } = connections;

  return (
    <div style={{minWidth: 260}}>
      <h3 style={{display: "flex", alignItems: "center", gap: "8px"}}>
        Server Controls
        {RECORD && (
          <div
            style={{
              width: "8px",
              height: "8px",
              backgroundColor: "#dc3545",
              borderRadius: "50%",
              animation: "pulse 1s infinite"
            }}
          />
        )}
      </h3>
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
          }
        `}
      </style>

      <div>
        <label>
          <input
            type="checkbox"
            checked={DRAW_LANDMARKS}
            onChange={(e) => {
              const newVal = e.target.checked;
              setSettings((prev) => ({ ...prev, DRAW_LANDMARKS: newVal }));
              sendStateToServer("DRAW_LANDMARKS", newVal);
            }}
          /> Draw Landmarks
        </label>
      </div>
      <div>
        <label>
          <input
            type="checkbox"
            checked={DRAW_FACE_BB}
            onChange={(e) => {
              const newVal = e.target.checked;
              setSettings((prev) => ({ ...prev, DRAW_FACE_BB: newVal }));
              sendStateToServer("DRAW_FACE_BB", newVal);
            }}
          /> Draw Face Boxes
        </label>
      </div>
      <div>
        <label>
          <input
            type="checkbox"
            checked={DRAW_SMILE_BB}
            onChange={(e) => {
              const newVal = e.target.checked;
              setSettings((prev) => ({ ...prev, DRAW_SMILE_BB: newVal }));
              sendStateToServer("DRAW_SMILE_BB", newVal);
            }}
          /> Draw Smile Boxes
        </label>
      </div>
      <div>
        <label>
          <input
            type="checkbox"
            checked={DRAW_ROTATED_BB}
            onChange={(e) => {
              const newVal = e.target.checked;
              setSettings((prev) => ({ ...prev, DRAW_ROTATED_BB: newVal }));
              sendStateToServer("DRAW_ROTATED_BB", newVal);
            }}
          /> Draw Rotated Boxes (must have Box enabled first)
        </label>
      </div>
      <div>
        <button
          onClick={() => {
            const newVal = !RECORD;
            setSettings((prev) => ({ ...prev, RECORD: newVal }));
            sendStateToServer("RECORD", newVal);
          }}
          style={{
            backgroundColor: RECORD ? "#dc3545" : "#28a745",
            color: "white",
            border: "none",
            padding: "8px 16px",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "bold"
          }}
        >
          {RECORD ? "Stop Recording" : "Start Recording"}
        </button>
      </div>
      <div style={{marginTop: 8}}>
        <label style={{display: "flex", alignItems: "center", gap: 8}}>
          <input
            type="checkbox"
            checked={!!TEST_MODE}
            onChange={(e) => {
              const newVal = e.target.checked;
              setSettings((prev) => ({ ...prev, TEST_MODE: newVal }));
              sendStateToServer("TEST_MODE", newVal);
            }}
          /> Test Mode (cycle sample faces)
        </label>
      </div>
      <div style={{marginTop: 8}}>
        <button
          onClick={() => {
            sendStateToServer("RESET_TILT", true);
          }}
          style={{
            backgroundColor: "#0d6efd",
            color: "white",
            border: "none",
            padding: "6px 12px",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "13px",
          }}
        >
          Reset Tilt (New Faces)
        </button>
      </div>
      <hr/>
      <div style={{marginTop:12}}>
        <div>Data Connection: {dataConnected ? "Connected" : "Disconnected"}</div>
        <div>Video Stream: {videoConnected ? "Connected" : "Disconnected"}</div>
        <div>Faces: {facesCount}</div>
      </div>
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
  );
}


