
from fastapi import WebSocket
import time

class ControlsManager:
    def __init__(self):
        self.active: set[WebSocket] = set()
        self.client_ping_times: dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)
        self.client_ping_times.pop(websocket, None)

    async def send_json(self, data: dict):
        stale = []
        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(ws)
        for s in stale:
            self.disconnect(s)

    async def recv_from(self, websocket: WebSocket):
        try:
            return await websocket.receive_text()
        except Exception:
            return None

    def update_ping_time(self, websocket: WebSocket):
        """Update the last ping time for a client"""
        self.client_ping_times[websocket] = time.time()

    def get_stale_connections(self, timeout_seconds: float = 21.0):
        """Get connections that haven't pinged in timeout_seconds"""
        current_time = time.time()
        stale = []
        for websocket, last_ping in self.client_ping_times.items():
            if current_time - last_ping > timeout_seconds:
                stale.append(websocket)
        return stale

    async def cleanup_stale_connections(self, timeout_seconds: float = 21.0):
        """Remove connections that haven't pinged recently"""
        stale = self.get_stale_connections(timeout_seconds)
        for websocket in stale:
            print(f"Removing stale connection: {websocket}")
            self.disconnect(websocket)
            try:
                await websocket.close(code=1000, reason="No ping received")
            except Exception:
                pass
