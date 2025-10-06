// src/App.js
import React, { useEffect, useState } from "react";
import SmileViewer from "./SmileViewer";

function App(){
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    // Handle page unload/refresh cleanup
    const handleBeforeUnload = (event) => {
      console.log("Page is being unloaded, cleaning up resources...");
      // The cleanup will be handled by React's useEffect cleanup functions
    };

    const handleUnload = () => {
      console.log("Page unloaded");
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('unload', handleUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleUnload);
    };
  }, []);

  return (
    <div style={{padding:20}}>
      <h2 style={{display: "flex", alignItems: "center", gap: "8px"}}>
        Smile Viewer
        {isRecording && (
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
      </h2>
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
          }
        `}
      </style>
      <SmileViewer onRecordChange={setIsRecording} />
    </div>
  );
}

export default App;

