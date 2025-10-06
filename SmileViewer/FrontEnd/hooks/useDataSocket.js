import { useEffect, useRef, useState, useCallback } from "react";

// Handles the data/control WebSocket: settings sync and faces list updates
export default function useDataSocket(resolvedWsUrl) {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeoutRef = useRef(null);
  const retryAttemptsRef = useRef(0);

  const facesRef = useRef([]);
  const [facesTick, setFacesTick] = useState(0);

  const [settings, setSettings] = useState({
    DRAW_LANDMARKS: false,
    DRAW_FACE_BB: false,
    DRAW_SMILE_BB: true,
    DRAW_ROTATED_BB: false,
    RECORD: false,
    TEST_MODE: false,
  });

  // Exponential backoff reconnect
  useEffect(() => {
    let closedByEffectCleanup = false;
    let currentSocket = null;

    function scheduleReconnect() {
      if (closedByEffectCleanup) return;
      const attempt = Math.min(retryAttemptsRef.current + 1, 6);
      retryAttemptsRef.current = attempt;
      const delayMs = Math.min(30000, 1000 * Math.pow(2, attempt - 1));
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(connect, delayMs);
    }

    function connect() {
      if (closedByEffectCleanup) return;
      try {
        const socket = new WebSocket(resolvedWsUrl);
        currentSocket = socket;
        setWs(socket);

        socket.onopen = () => {
          if (closedByEffectCleanup) {
            socket.close();
            return;
          }
          setConnected(true);
          retryAttemptsRef.current = 0;
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
          // Request current settings from server
          socket.send(JSON.stringify({ type: "get_settings" }));
        };

        socket.onmessage = (ev) => {
          if (closedByEffectCleanup) return;
          if (typeof ev.data !== "string") return;
          try {
            const payload = JSON.parse(ev.data);
            if (payload.t === "f") {
              const compact = (payload.f || []).slice(0, 3);
              facesRef.current = compact.map((row) => {
                const smiling = row[9];
                const face_bbox = row[1] >= 0 ? [row[1], row[2], row[3], row[4]] : null;
                const smile_bbox = smiling == "Smiling" ? [row[5], row[6], row[7], row[8]] : [-1, -1, -1, -1];
                return {
                  face_id: row[0],
                  face_bbox,
                  smile_bbox,
                  smile_status: smiling,
                  landmarks: row.length > 10 ? row[10] : null,
                };
              });
              setFacesTick((t) => (t + 1) % 1000000);
            } else if (payload.type === "faces") {
              const faces = Array.isArray(payload.faces) ? payload.faces.slice(0, 3) : [];
              facesRef.current = faces.map((f) => ({
                face_id: f.face_id,
                face_bbox: f.face_bbox || null,
                smile_bbox: f.smile_bbox || [-1, -1, -1, -1],
                smile_status: f.smile_status,
                landmarks: null,
              }));
              setFacesTick((t) => (t + 1) % 1000000);
            } else if (payload.type === "settings_update") {
              if (payload.key && payload.value !== undefined) {
                setSettings((prev) => ({ ...prev, [payload.key]: payload.value }));
              }
            } else if (payload.type === "current_settings") {
              if (payload.settings) {
                setSettings({
                  DRAW_LANDMARKS: !!payload.settings.DRAW_LANDMARKS,
                  DRAW_FACE_BB: !!payload.settings.DRAW_FACE_BB,
                  DRAW_SMILE_BB: !!payload.settings.DRAW_SMILE_BB,
                  DRAW_ROTATED_BB: !!payload.settings.DRAW_ROTATED_BB,
                  RECORD: !!payload.settings.RECORD,
                  TEST_MODE: !!payload.settings.TEST_MODE,
                });
              }
            }
          } catch (e) {
            // ignore parse errors
          }
        };

        socket.onerror = () => {};

        socket.onclose = () => {
          setConnected(false);
          if (!closedByEffectCleanup) {
            scheduleReconnect();
          }
        };
      } catch (err) {
        if (!closedByEffectCleanup) scheduleReconnect();
      }
    }

    connect();

    return () => {
      closedByEffectCleanup = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (currentSocket) {
        try {
          if (
            currentSocket.readyState === WebSocket.OPEN ||
            currentSocket.readyState === WebSocket.CONNECTING
          ) {
            currentSocket.close(1000, "Component unmounting");
          }
        } catch {}
        currentSocket = null;
      }
    };
  }, [resolvedWsUrl]);

  const sendStateToServer = useCallback(
    (key, value) => {
      const message = { type: "set_state", key, value };
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify(message));
          return true;
        } catch {
          return false;
        }
      }
      return false;
    },
    [ws]
  );

  // Heartbeat
  useEffect(() => {
    const interval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ type: "ping" })); } catch {}
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [ws]);

  return {
    ws,
    connected,
    facesRef,
    facesTick,
    settings,
    setSettings,
    sendStateToServer,
  };
}


