import { useEffect, useRef, useState } from "react";

// Manages the video WebSocket and renders frames into a provided canvas ref
export default function useVideoSocket(resolvedWsUrl, videoCanvasRef) {
  const [videoWs, setVideoWs] = useState(null);
  const [videoConnected, setVideoConnected] = useState(false);
  const videoReconnectTimeoutRef = useRef(null);
  const videoRetryAttemptsRef = useRef(0);
  const isDrawingRef = useRef(false);
  const pendingFrameRef = useRef(null);

  useEffect(() => {
    let closedByEffectCleanup = false;
    let currentVideoSocket = null;

    function scheduleVideoReconnect() {
      if (closedByEffectCleanup) return;
      const attempt = Math.min(videoRetryAttemptsRef.current + 1, 6);
      videoRetryAttemptsRef.current = attempt;
      const delayMs = Math.min(30000, 1000 * Math.pow(2, attempt - 1));
      if (videoReconnectTimeoutRef.current) clearTimeout(videoReconnectTimeoutRef.current);
      videoReconnectTimeoutRef.current = setTimeout(connectVideo, delayMs);
    }

    function connectVideo() {
      if (closedByEffectCleanup) return;
      try {
        const videoUrl = resolvedWsUrl.replace('/controls', '/video');
        const videoSocket = new WebSocket(videoUrl);
        try { videoSocket.binaryType = "arraybuffer"; } catch {}
        currentVideoSocket = videoSocket;
        setVideoWs(videoSocket);

        videoSocket.onopen = () => {
          if (closedByEffectCleanup) {
            videoSocket.close();
            return;
          }
          setVideoConnected(true);
          videoRetryAttemptsRef.current = 0;
          if (videoReconnectTimeoutRef.current) {
            clearTimeout(videoReconnectTimeoutRef.current);
            videoReconnectTimeoutRef.current = null;
          }
        };

        videoSocket.onmessage = (ev) => {
          if (closedByEffectCleanup) return;
          if (ev.data instanceof ArrayBuffer || (typeof Blob !== 'undefined' && ev.data instanceof Blob)) {
            const handleBlob = (blob) => {
              const img = new Image();
              img.onload = () => {
                if (!videoCanvasRef.current || closedByEffectCleanup) {
                  isDrawingRef.current = false;
                  URL.revokeObjectURL(img.src);
                  return;
                }
                const ctx = videoCanvasRef.current.getContext('2d');
                if (videoCanvasRef.current.width !== img.width || videoCanvasRef.current.height !== img.height) {
                  videoCanvasRef.current.width = img.width;
                  videoCanvasRef.current.height = img.height;
                }
                ctx.drawImage(img, 0, 0);
                isDrawingRef.current = false;
                URL.revokeObjectURL(img.src);
                if (pendingFrameRef.current) {
                  const next = pendingFrameRef.current;
                  pendingFrameRef.current = null;
                  isDrawingRef.current = true;
                  handleBlob(next);
                }
              };
              img.onerror = () => { isDrawingRef.current = false; };
              const url = URL.createObjectURL(blob);
              img.src = url;
            };
            const blob = ev.data instanceof Blob ? ev.data : new Blob([ev.data], { type: 'image/jpeg' });
            if (isDrawingRef.current) {
              pendingFrameRef.current = blob;
            } else {
              isDrawingRef.current = true;
              handleBlob(blob);
            }
            return;
          }

          if (typeof ev.data === "string") {
            try {
              const payload = JSON.parse(ev.data);
              if (payload.type === "video_frame" && payload.frame && videoCanvasRef.current) {
                const drawFrame = (dataUrl) => {
                  const img = new Image();
                  img.onload = () => {
                    if (!videoCanvasRef.current || closedByEffectCleanup) { isDrawingRef.current = false; return; }
                    const ctx = videoCanvasRef.current.getContext('2d');
                    if (videoCanvasRef.current.width !== img.width || videoCanvasRef.current.height !== img.height) {
                      videoCanvasRef.current.width = img.width;
                      videoCanvasRef.current.height = img.height;
                    }
                    ctx.drawImage(img, 0, 0);
                    isDrawingRef.current = false;
                    if (pendingFrameRef.current) {
                      const next = pendingFrameRef.current;
                      pendingFrameRef.current = null;
                      isDrawingRef.current = true;
                      drawFrame(next);
                    }
                  };
                  img.onerror = () => { isDrawingRef.current = false; };
                  img.src = dataUrl;
                };
                const dataUrl = `data:image/jpeg;base64,${payload.frame}`;
                if (isDrawingRef.current) {
                  pendingFrameRef.current = dataUrl;
                } else {
                  isDrawingRef.current = true;
                  drawFrame(dataUrl);
                }
              }
            } catch {}
          }
        };

        videoSocket.onerror = () => {};
        videoSocket.onclose = () => {
          setVideoConnected(false);
          if (!closedByEffectCleanup) scheduleVideoReconnect();
        };
      } catch (err) {
        if (!closedByEffectCleanup) scheduleVideoReconnect();
      }
    }

    connectVideo();

    return () => {
      closedByEffectCleanup = true;
      if (videoReconnectTimeoutRef.current) {
        clearTimeout(videoReconnectTimeoutRef.current);
        videoReconnectTimeoutRef.current = null;
      }
      if (currentVideoSocket) {
        try {
          if (
            currentVideoSocket.readyState === WebSocket.OPEN ||
            currentVideoSocket.readyState === WebSocket.CONNECTING
          ) {
            currentVideoSocket.close(1000, "Component unmounting");
          }
        } catch {}
        currentVideoSocket = null;
      }
    };
  }, [resolvedWsUrl, videoCanvasRef]);

  // Heartbeat
  useEffect(() => {
    const interval = setInterval(() => {
      if (videoWs && videoWs.readyState === WebSocket.OPEN) {
        try { videoWs.send(JSON.stringify({ type: "ping" })); } catch {}
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [videoWs]);

  return { videoWs, videoConnected };
}


