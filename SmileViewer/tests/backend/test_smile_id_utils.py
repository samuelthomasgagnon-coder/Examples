from types import SimpleNamespace
from Server.Smile_ID import SmileIDer


def test_check_occlusion_overlap_and_no_overlap():
    assert SmileIDer.check_occlusion((0, 0, 10, 10), (5, 5, 15, 15)) is True
    assert SmileIDer.check_occlusion((0, 0, 10, 10), (11, 11, 20, 20)) is False


def test_calculate_mar_basic_ratio():
    # Build minimal landmark set with required indices 13, 14, 61, 291
    landmarks = [SimpleNamespace(x=0.0, y=0.0) for _ in range(292)]
    # Horizontal corners
    landmarks[61] = SimpleNamespace(x=0.0, y=0.0)
    landmarks[291] = SimpleNamespace(x=2.0, y=0.0)
    # Vertical distance
    landmarks[13] = SimpleNamespace(x=1.0, y=1.0)
    landmarks[14] = SimpleNamespace(x=1.0, y=0.0)

    mar = SmileIDer.calculate_mar(landmarks)
    # vertical = 1, horizontal = 2 -> 0.5
    assert abs(mar - 0.5) < 1e-6


