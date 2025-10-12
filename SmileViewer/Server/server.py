import cv2
import time
import signal
import argparse

import asyncio 
from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import glob

from WS_multi_socket import MultiSocketManager
from DB_manager import DBmanager
from Smile_ID import SmileIDer

class SmileAnalysisServer:
    def __init__(self):
        # Build state dict (no module-level globals downstream)
        self.state, self.controls = self.init_standard_config()
        signal.signal(signal.SIGINT, self.signal_handler)
        # Build FastAPI app with lifespan controlled by this instance
        self.LandmarksSubSets = {}
        self.SmileIDer = SmileIDer(self)
        self.SmileIDer.controls = self.controls
        self.SmileIDer.DB_manager = DBmanager()
        self.DB_manager = self.SmileIDer.DB_manager
        self.SmileIDer.state = self.state
        self.app = FastAPI(lifespan=self.lifespan)
        # Register websockets against this app
        self.MultiSocketManager = MultiSocketManager(self)
        self.MultiSocketManager.register(self.app, self)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.state['shutdown_event'].set()
        # Give a moment for the shutdown event to propagate
        import time
        time.sleep(0.1)
    
    @staticmethod
    def init_standard_config():
        # Initialize Camera
        webcam = cv2.VideoCapture(0)
        if not webcam.isOpened():
            raise RuntimeError("Could not open camera")
        
        max_fps = webcam.get(cv2.CAP_PROP_FPS)
        if max_fps <= 1:
            print(f"Warning: Camera returned invalid FPS: {max_fps}. Defaulting to 30 FPS.")
            max_fps = 30
        
        CLEAR_TIME = 0.33
        MIN_VISIBILITY_FRAMES = int(max_fps * CLEAR_TIME)
        
        state = {
            # States and Runtime
            "latest_frame": None,
            "shutdown_event": asyncio.Event(),
            "persistent_faces": {},
            "hands_in_frame": [],
            "Video_Connections": {},
            # Test mode state
            "test_images": None,
            "test_image_index": 0,
            "test_last_switch_ts": 0.0,

            # Camera Configuration
            "webcam": webcam,
            "max_fps": max_fps,
        }
        controls = {
            # Face and Smile Detection controlsuration
            "CLEAR_TIME": CLEAR_TIME,
            "MIN_VISIBILITY_FRAMES": MIN_VISIBILITY_FRAMES,
            "FRAME_HISTORY_LEN": MIN_VISIBILITY_FRAMES,
            "PF_SHIFT_BUFF": 0.15,
            "MAR_VAR_THRESHOLD": 0.005,
            "SMILE_THRESH": 0.35,
            "SMILE_CONFIDENCE": 0.9,
            "MAR_NEUTRAL_THRESHOLD": 0.005,
            "FAR_TILT_TOLERANCE": 0.92,
            
            # Drawing and Display Settings
            "FACE_PAD": 22,
            "SMILE_PAD": 7,
            "HAND_PAD": 7,
            "DRAW_LANDMARKS": False,
            "DRAW_FACE_BB": False,
            "DRAW_SMILE_BB": True,
            "DRAW_ROTATED_BB": False,
            "RECORD": False,
            "ROTATED_BB_FRAME_AVERAGE": 3,
            # QOL controls
            "TEST_MODE": False,
        }
        ''' UNUSED ATM 
        # Multiprocessing Queues
        "face_recognition_queue": Queue(),
        "smile_crop_queue": Queue(),
        "smile_metadata_queue": Queue(),'''
        return state, controls

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        task = asyncio.create_task(self.loop())
        try:
            yield
        finally:
            print("FastAPI lifespan: Starting shutdown process...")
            try:
                await asyncio.wait_for(self.state['shutdown_event'].wait(), timeout=2.0)
            except asyncio.TimeoutError:
                print("Shutdown timeout reached, forcing cleanup...")
            if not task.done():
                print("Cancelling main loop task...")
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    print("Main loop task cancelled or timed out")
            self.cleanup_resources()
            print("FastAPI lifespan: Shutdown process completed")

    def flush_persistent_faces(self):
        """Cancel workers and remove all tracked faces."""
        s = self.state
        for face_id, face_data in list(s['persistent_faces'].items()):
            try:
                if 'worker_task' in face_data and face_data['worker_task'] and not face_data['worker_task'].done():
                    face_data['worker_task'].cancel()
            except Exception:
                pass
        s['persistent_faces'].clear()

    async def Send_Data_update(self):
        now = time.time()
        s = self.state
        c = self.controls
        if len(self.MultiSocketManager.ControlsManager.active) > 0:
            compact = []
            for  face_id, f in s['persistent_faces'].items():
                x1, y1, x2, y2 = f['face_bbox']
                if f.get('smile_bbox'):
                    sx1, sy1, sx2, sy2 = f['smile_bbox']
                else:
                    sx1, sy1, sx2, sy2 = (-1, -1, -1, -1)
                row = [face_id, x1, y1, x2, y2, sx1, sy1, sx2, sy2, f['smile_status'] ]
                if c['DRAW_LANDMARKS']:
                    w, h = s['w'], s['h']
                    all_landparks = f['landmarks']
                    subset = self.SmileIDer.LandmarksSubSets['face_mesh_subset']
                    landmarks = [[int(all_landparks[i].x * w), int(all_landparks[i].y * h)] for i in subset]
                    row.append(landmarks)
                compact.append(row)
            faces_msg = {"t": "f", "ts": now, "f": compact}
            await self.MultiSocketManager.ControlsManager.send_json(faces_msg)

    async def loop(self):
        s = self.state
        c = self.controls
        #ct = time.time()
        try:
            while not s['shutdown_event'].is_set():
                # Decide frame source: webcam or test images
                if not c.get('TEST_MODE', False):
                    ret, frame =  await asyncio.to_thread(s['webcam'].read)
                    if not ret:
                        await asyncio.sleep(0.03)
                        continue
                else:
                    # Initialize test images is needed
                    if s['test_images'] is None:
                        faces_dir = os.path.join(os.getcwd(), "Samples", "Faces")
                        image_paths = sorted(
                            glob.glob(os.path.join(faces_dir, "*.jpg")) +
                            glob.glob(os.path.join(faces_dir, "*.jpeg")) +
                            glob.glob(os.path.join(faces_dir, "*.png"))
                        )
                        s['test_images'] = image_paths if image_paths else []
                        s['test_image_index'] = 0
                        s['test_last_switch_ts'] = 0.0
                        print(image_paths)
                    # If no images available, fallback to webcam
                    if not s['test_images']:
                        ret, frame = await asyncio.to_thread(s['webcam'].read)
                        if not ret:
                            await asyncio.sleep(0.03)
                            continue
                    else:
                        await asyncio.sleep(1.25)
                        s['test_image_index'] = (s['test_image_index'] + 1) % len(s['test_images'])
                        img_path = s['test_images'][s['test_image_index']]
                        frame = cv2.imread(img_path)
                        if frame is None:
                            # Skip bad image and try next
                            s['test_images'].pop(s['test_image_index'])
                            if not s['test_images']:
                                continue
                            s['test_image_index'] %= len(s['test_images'])
                            continue
                # front faceing so flip -> more like a mirror
                frame = cv2.flip(frame, 1)
                s['latest_frame'] = frame.copy() # Store a copy for async workers
                #need h,w for scale info on mediapipe outputs
                s['h'], s['w'], _ = frame.shape
                #BGR -> RGB
                rgb_frame = cv2.cvtColor(s['latest_frame'], cv2.COLOR_BGR2RGB)
                #get hands and faces
                self.SmileIDer.get_hands(rgb_frame, frame)
                #check faces in frame, no need for them to persist
                current_faces_in_frame = self.SmileIDer.get_faces(rgb_frame, frame)
                #Match, Update, Add Faces to persistent faces
                self.SmileIDer.check_faces(current_faces_in_frame)
                #Process and Draw tracked Faces
                self.SmileIDer.process_faces(frame)
                # Broadcast annotated video frame to WebRTC clients
                await self.MultiSocketManager.broadcast_video_frame(frame)
                await self.Send_Data_update()
                #ut = time.time() 
                #fps = 1.0 / (ut - ct) if (ut - ct) > 0 else 0
                #print(f"{fps:.1f} FPS")
                #ct = ut

        except asyncio.CancelledError:
            print("Main loop cancelled, shutting down...")
            raise
        except Exception as e:
            print(f"Error in main loop: {e}")
            raise

    def cleanup_resources(self):
        """Clean up all resources before exit"""
        s = self.state
        persistent_faces = s['persistent_faces']
        webcam = s['webcam']
        self.DB_manager.cleanup_resources()
        self.MultiSocketManager.cleanup_resources()
        # Cancel all running tasks
        print("Cancelling background tasks...")
        for face_id, face_data in list(persistent_faces.items()):
            if 'worker_task' in face_data and not face_data['worker_task'].done():
                face_data['worker_task'].cancel()
        
        # Release camera
        if webcam and webcam.isOpened():
            webcam.release()
            print("Camera released.")
        
        
        print("Cleanup completed.")

def create_app():
    """Uvicorn app factory."""
    analysis_instance = SmileAnalysisServer()
    return analysis_instance.app

def main():
    parser = argparse.ArgumentParser(description="Run SmileViewer FastAPI server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    import uvicorn
    if args.reload:
        # In reload mode, uvicorn requires an import string; use factory
        uvicorn.run("server:create_app", factory=True, host=args.host, port=args.port, reload=True)
    else:
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()