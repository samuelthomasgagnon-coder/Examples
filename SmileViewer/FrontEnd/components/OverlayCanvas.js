import React, { useEffect, useRef } from "react";

// Draws faces overlays according to current video canvas size
export default function OverlayCanvas({ videoCanvasRef, drawFaceBB, drawSmileBB, drawLandmarks, facesRef }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    let rafId = 0;
    let isActive = true;

    function drawOverlay() {
      if (!isActive) return;
      const vidCanvas = videoCanvasRef.current;
      const canvas = canvasRef.current;
      if (vidCanvas && canvas) {
        const ctx = canvas.getContext("2d");
        // Match overlay canvas to video canvas size
        if (vidCanvas.width && vidCanvas.height) {
          if (canvas.width !== vidCanvas.width || canvas.height !== vidCanvas.height) {
            canvas.width = vidCanvas.width;
            canvas.height = vidCanvas.height;
          }
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          const faces = facesRef.current;
          faces.forEach((f) => {
            const fb = f.face_bbox;
            if (fb && drawFaceBB) {
              const [x1, y1, x2, y2] = fb;
              ctx.strokeStyle = "lime";
              ctx.lineWidth = 2;
              ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
              ctx.font = "14px sans-serif";
              ctx.fillStyle = "lime";
              ctx.fillText(`Face ${f.face_id}: ${f.smile_status}`, x1, Math.max(12, y1 - 6));
            }
            if (f.smile_bbox && drawSmileBB) {
              const [sx1, sy1, sx2, sy2] = f.smile_bbox;
              ctx.strokeStyle = "orange";
              ctx.lineWidth = 2;
              ctx.strokeRect(sx1, sy1, sx2 - sx1, sy2 - sy1);
            }
            if (drawLandmarks && f.landmarks && Array.isArray(f.landmarks)) {
              ctx.fillStyle = "deepskyblue";
              f.landmarks.forEach(([lx, ly]) => {
                ctx.beginPath();
                ctx.arc(lx, ly, 2, 0, Math.PI * 2);
                ctx.fill();
              });
            }
          });
        }
      }
      if (isActive) rafId = requestAnimationFrame(drawOverlay);
    }

    rafId = requestAnimationFrame(drawOverlay);
    return () => {
      isActive = false;
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [videoCanvasRef, drawFaceBB, drawSmileBB, drawLandmarks, facesRef]);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: "absolute", inset: 0, pointerEvents: "none", width: "100%", height: "100%" }}
    />
  );
}

