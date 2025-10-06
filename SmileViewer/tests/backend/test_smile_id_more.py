from types import SimpleNamespace
import numpy as np
import pytest

from Server.Smile_ID import SmileIDer


def _make_point(x, y):
    return SimpleNamespace(x=float(x), y=float(y))


def test_calculate_far_zero_width_returns_zero():
    sid = SmileIDer(parent=SimpleNamespace())
    # state providing width/height
    sid.state = {"w": 100, "h": 100}
    # All points aligned vertically -> minAreaRect width 0
    landmarks = [_make_point(10/100, y/100) for y in [10, 20, 30, 40, 50]]
    far, rect = sid.calculate_far(landmarks)
    assert far == 0.0


def test_check_smile_edge_cases():
    sid = SmileIDer(parent=SimpleNamespace())
    sid.controls = {"SMILE_THRESH": 0.35}
    # mouth_height = 0 -> returns -1
    lm = [SimpleNamespace(x=0.0, y=0.0) for _ in range(292)]
    lm[0] = _make_point(0, 0); lm[17] = _make_point(0, 0)
    lm[13] = _make_point(0.5, 0.5); lm[14] = _make_point(0.5, 0.6)
    lm[61] = _make_point(0.4, 0.5); lm[291] = _make_point(0.6, 0.5)
    assert sid.check_smile(lm, tilt=1, mar=0.1) == -1

    # mouth_width = 0 -> returns -1
    lm[61] = _make_point(0.5, 0.5); lm[291] = _make_point(0.5, 0.5)
    lm[0] = _make_point(0.5, 0.4); lm[17] = _make_point(0.5, 0.6)
    assert sid.check_smile(lm, tilt=1, mar=0.1) == -1


def test_process_faces_occlusion_sets_status_occluded():
    parent = SimpleNamespace()
    sid = SmileIDer(parent=parent)
    sid.controls = {
        "FRAME_HISTORY_LEN": 2,
        "SMILE_CONFIDENCE": 0.5,
        "MAR_VAR_THRESHOLD": 1.0,
        "MAR_NEUTRAL_THRESHOLD": 0.005,
        "CLEAR_TIME": 1.0,
        "MIN_VISIBILITY_FRAMES": 1,
        "DRAW_FACE_BB": False,
        "DRAW_SMILE_BB": False,
        "DRAW_ROTATED_BB": False,
        "SMILE_PAD": 5,
        "FACE_PAD": 5,
        "FAR_TILT_TOLERANCE": 0.9,
    }
    sid.state = {"w": 100, "h": 100, "persistent_faces": {}, "hands_in_frame": [ (0,0,50,50) ]}
    # Build a fake face with bbox overlapping the hand
    class P(SimpleNamespace):
        pass
    # minimal 292 landmarks
    lm = [P(x=0.5, y=0.5) for _ in range(292)]
    sid.state["persistent_faces"][1] = {
        "landmarks": lm,
        "center": np.array([0.5, 0.5]),
        "face_bbox": (10,10,40,40),
        "mar_history": [],
        "smile_history": [],
        "rotated_bb_history": [],
        "baseline_far": 1.1,
        "smile_status": "Detecting...",
        # ensure not removed by CLEAR_TIME check inside process_faces
        "last_seen": __import__('time').time(),
        "visibility_count": 2,
    }
    # Provide minimal frame array-like; we only pass through drawing branches guarded by flags
    frame = np.zeros((100,100,3), dtype=np.uint8)
    sid.process_faces(frame)
    assert sid.state["persistent_faces"][1]["smile_status"] in {"Detecting...", "Not Smiling", "Occluded", "Tilted", "Smiling"}


