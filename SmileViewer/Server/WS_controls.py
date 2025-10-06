
from fastapi import WebSocket

class ControlsManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

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
