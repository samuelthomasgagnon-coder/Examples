


import asyncio 
import time
import json
import cv2

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from WS_controls import ControlsManager

class MultiSocketManager:
    def __init__(self, parent):
        self.ControlsManager = ControlsManager()
        self.parent = parent

    def cleanup_resources(self):
        """Clean up all resources before exit"""
        manager = self.ControlsManager
        s = self.parent.state
        if manager and hasattr(manager, 'active'):
            for websocket in list(manager.active):
                try:
                    # Send close message to clients
                    asyncio.create_task(websocket.close(code=1000, reason="Server shutting down"))
                except Exception as e:
                    print(f"Error closing data WebSocket: {e}")
            manager.active.clear()
        
        # Close video WebSocket connections
        for client_id, websocket in list(s['Video_Connections'].items()):
            try:
                asyncio.create_task(websocket.close(code=1000, reason="Server shutting down"))
            except Exception as e:
                print(f"Error closing video WebSocket {client_id}: {e}")
        s['Video_Connections'].clear()
        print("Sockets cleanup completed.")

    # Frame encoding utilities
    @staticmethod
    def cvframe_to_jpeg_bytes(frame):
        try:
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                return None
            # Convert numpy buffer to raw bytes for binary WebSocket send
            return buffer.tobytes()
        except Exception as e:
            print(f"Error encoding frame to JPEG: {e}")
            return None

    def register(self, app: FastAPI, analysis_instance):
        self.analysis = analysis_instance
        app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_methods=['*'],
            allow_headers=['*'],
        )

        @app.websocket("/controls")
        async def controls_endpoint(websocket: WebSocket):
            s = self.parent.state
            c = self.parent.controls
            await self.ControlsManager.connect(websocket)
            try:
                while True:
                    try:
                        msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0) #check for toggle
                        #print(f"Data WS received: {msg}")
                        try:
                            payload = json.loads(msg)
                            #print(f"Parsed payload: {payload}")
                            if payload.get("type") == "set_state":
                                key = payload.get("key")
                                value = payload.get("value")
                                if key in c:
                                    # cast to existing control type
                                    current_type = type(c[key])
                                    try:
                                        if current_type is bool:
                                            if isinstance(value, str):
                                                cast_value = value.lower() in ("1","true","t","yes","y","on")
                                            else:
                                                cast_value = bool(value)
                                        else:
                                            cast_value = current_type(value)
                                    except Exception:
                                        cast_value = c[key]
                                    c[key] = cast_value
                                    # broadcast new settings to everyone EXCEPT the sender
                                    settings_update = {"type":"settings_update","key":key,"value":c[key]}
                                    
                                    # Send to other data WebSocket clients (not the sender)
                                    for ws_client in list(self.ControlsManager.active):
                                        if ws_client != websocket:  # Don't send back to sender
                                            try:
                                                await ws_client.send_json(settings_update)
                                            except Exception as e:
                                                print(f"Error sending settings update to data client: {e}")
                                    
                                    # Do not send settings over the video WebSocket
                                elif key == "RESET_TILT":
                                    # Flush persistent faces to reset tilt baselines and state
                                    try:
                                        self.parent.flush_persistent_faces()
                                    except Exception as e:
                                        print(f"Error flushing persistent faces: {e}")
                                else:
                                    print(f"Global variable {key} not found")
                            elif payload.get("type") == "get_settings":
                                settings = {
                                    "DRAW_LANDMARKS": c['DRAW_LANDMARKS'],
                                    "DRAW_FACE_BB": c['DRAW_FACE_BB'],
                                    "DRAW_SMILE_BB": c['DRAW_SMILE_BB'],
                                    "DRAW_ROTATED_BB": c['DRAW_ROTATED_BB'],
                                    "RECORD": c['RECORD'],
                                    "ROTATED_BB_FRAME_AVERAGE": c['ROTATED_BB_FRAME_AVERAGE'],
                                    "TEST_MODE": c.get('TEST_MODE', False),
                                }
                                await websocket.send_json({"type": "current_settings", "settings": settings})
                            elif payload.get("type") == "ping":
                                #print("Received ping from data WebSocket - sending pong")
                                await websocket.send_json({"type": "pong"})
                        except Exception as e:
                            print(f"Error processing data WebSocket message: {e}")
                            pass
                    except asyncio.TimeoutError:
                        # no message arrived - keep connection alive
                        # Don't log every timeout to reduce noise
                        pass
            except WebSocketDisconnect:
                self.ControlsManager.disconnect(websocket)
            except Exception:
                self.ControlsManager.disconnect(websocket)

        @app.websocket("/video")
        async def video_stream_endpoint(websocket: WebSocket):
            """WebSocket endpoint for video streaming"""
            s = self.parent.state
            c = self.parent.controls
            await websocket.accept()
            client_id = f"client_{int(time.time() * 1000)}"
            s['Video_Connections'][client_id] = websocket
            
            #print(f"Video client connected: {client_id}")
            #print(f"Video WebSocket connected. Active video connections: {len(Video_Connections)}")
            
            try:
                while True:
                    try:
                        # Wait for client messages (like toggle requests)
                        msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                        #print(f"Video WS received: {msg}")
                        try:
                            payload = json.loads(msg)
                            #print(f"Video WS parsed payload: {payload}")
                            if payload.get("type") == "ping":
                                #print("Received ping from video WebSocket - sending pong")
                                await websocket.send_json({"type": "pong"})
                            # do not handle settings on video websocket
                        except Exception as e:
                            print(f"Error processing video WebSocket message: {e}")
                    except asyncio.TimeoutError:
                        # No message received - keep connection alive
                        # Don't log every timeout to reduce noise
                        pass
            except WebSocketDisconnect:
                pass
                #print(f"Video client disconnected: {client_id}")
            except Exception as e:
                print(f"Error in video stream: {e}")
            finally:
                s['Video_Connections'].pop(client_id, None)

        @app.get("/")
        async def root():
            s = self.parent.state
            return {"status":"running", "video_clients": len(s['Video_Connections'])}

        @app.get("/test-frame")
        async def test_frame():
            """Test endpoint to verify frame encoding (binary length only, no base64)"""
            s = self.parent.state
            if s['latest_frame'] is not None:
                jpeg_bytes = MultiSocketManager.cvframe_to_jpeg_bytes(s['latest_frame'])
                if jpeg_bytes:
                    return {
                        "status": "success",
                        "byte_length": len(jpeg_bytes),
                        "frame_shape": s['latest_frame'].shape if hasattr(s['latest_frame'], 'shape') else "unknown"
                    }
            return {"status": "no_frame_available"}

        @app.get("/debug")
        async def debug_info():
            """Debug endpoint to check system status"""
            s = self.parent.state
            c = self.parent.controls
            return {
                "video_clients": len(s['Video_Connections']),
                "latest_frame_available": s['latest_frame'] is not None,
                "webcam_opened": s['webcam'].isOpened() if s['webcam'] else False,
                "shutdown_event_set": s['shutdown_event'].is_set(),
                "global_settings": {
                    "DRAW_LANDMARKS": c['DRAW_LANDMARKS'],
                    "DRAW_FACE_BB": c['DRAW_FACE_BB'],
                    "DRAW_SMILE_BB": c['DRAW_SMILE_BB'],
                    "DRAW_ROTATED_BB": c['DRAW_ROTATED_BB'],
                    "RECORD": c['RECORD']
                }
            }

        @app.get("/test-broadcast")
        async def test_broadcast():
            """Test endpoint to manually trigger a frame broadcast"""
            s = self.parent.state
            # Grab a fresh frame to avoid re-sending stale content
            try:
                if s['webcam'] and s['webcam'].isOpened():
                    ret, frame = s['webcam'].read()
                    if ret:
                        frame = cv2.flip(frame, 1)
                        s['latest_frame'] = frame.copy()
                        s['h'], s['w'], _ = frame.shape
            except Exception:
                pass
            if s['latest_frame'] is not None and s['Video_Connections']:
                await self.broadcast_video_frame(s['latest_frame'])
                return {"status": "frame_broadcasted", "clients": len(s['Video_Connections'])}
            return {"status": "no_frame_or_clients", "frame_available": s['latest_frame'] is not None, "clients": len(s['Video_Connections'])}

    async def broadcast_video_frame(self, frame):
        s = self.parent.state
        if not s['Video_Connections']:
            return
        jpeg_bytes = MultiSocketManager.cvframe_to_jpeg_bytes(frame)
        if jpeg_bytes is None:
            return
        disconnected_clients = []
        for client_id, websocket in s['Video_Connections'].items():
            try:
                # Send raw JPEG bytes over the binary WebSocket channel
                await websocket.send_bytes(jpeg_bytes)
            except Exception:
                disconnected_clients.append(client_id)
        for client_id in disconnected_clients:
            s['Video_Connections'].pop(client_id, None)
