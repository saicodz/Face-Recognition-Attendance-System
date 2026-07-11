"""
Tests for everything that doesn't require dlib/face_recognition to be
compiled, so they run fast and prove the surrounding logic is correct
independent of the face-matching model itself.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import cv2

from app.utils.image_utils import blur_score, brightness_score, assess_quality
from app.core.config import settings


def make_sharp_image():
    # checkerboard = lots of high-frequency edges -> high blur_score
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    img[::10, :] = 255
    img[:, ::10] = 255
    return img


def make_blurry_image():
    img = make_sharp_image()
    return cv2.GaussianBlur(img, (25, 25), 15)


def test_blur_detection_distinguishes_sharp_and_blurry():
    sharp = blur_score(make_sharp_image())
    blurry = blur_score(make_blurry_image())
    assert sharp > blurry, f"expected sharp({sharp}) > blurry({blurry})"
    print(f"PASS blur detection: sharp={sharp:.1f} blurry={blurry:.1f}")


def test_brightness_detects_dark_and_bright():
    dark = np.full((100, 100, 3), 10, dtype=np.uint8)
    bright = np.full((100, 100, 3), 250, dtype=np.uint8)
    assert brightness_score(dark) < 40
    assert brightness_score(bright) > 230
    print("PASS brightness detection")


def test_assess_quality_rejects_small_face():
    img = make_sharp_image()
    report = assess_quality(img, face_box=(0, 20, 20, 0))  # 20x20 px face
    assert not report.ok
    assert "small" in report.reason.lower()
    print(f"PASS rejects small face: {report.reason}")


def test_assess_quality_rejects_blurry_face():
    img = make_blurry_image()
    report = assess_quality(img, face_box=(0, 300, 300, 0))
    assert not report.ok
    print(f"PASS rejects blurry face: {report.reason}")


if __name__ == "__main__":
    test_blur_detection_distinguishes_sharp_and_blurry()
    test_brightness_detects_dark_and_bright()
    test_assess_quality_rejects_small_face()
    test_assess_quality_rejects_blurry_face()
    print("\nALL IMAGE QUALITY TESTS PASSED")
