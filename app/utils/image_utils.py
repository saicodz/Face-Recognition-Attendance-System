"""
Low-level image quality checks used during face registration.

Rejecting bad frames *before* they become a stored embedding is what
separates a robust system from a toy one: a single blurry/dark/duplicate
photo baked into the database silently degrades recognition accuracy for
that person forever.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from app.core.config import settings


@dataclass
class QualityReport:
    ok: bool
    reason: str = ""
    blur_score: float = 0.0
    brightness: float = 0.0


def blur_score(image_bgr: np.ndarray) -> float:
    """
    Variance of the Laplacian. Sharp images have high-frequency edges and
    thus high variance; blurry images look "smooth" and score low.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def brightness_score(image_bgr: np.ndarray) -> float:
    """Mean pixel intensity (0-255) as a crude but effective exposure check."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def assess_quality(image_bgr: np.ndarray, face_box: tuple[int, int, int, int]) -> QualityReport:
    """
    face_box is (top, right, bottom, left) as returned by face_recognition.
    Runs blur, exposure, and face-size checks and returns the first failure.
    """
    top, right, bottom, left = face_box
    face_w, face_h = right - left, bottom - top

    if face_w < settings.MIN_FACE_SIZE_PX or face_h < settings.MIN_FACE_SIZE_PX:
        return QualityReport(ok=False, reason="Face too small / too far from camera")

    b_score = blur_score(image_bgr)
    if b_score < settings.BLUR_THRESHOLD:
        return QualityReport(ok=False, reason="Image too blurry", blur_score=b_score)

    bright = brightness_score(image_bgr)
    if bright < 40:
        return QualityReport(ok=False, reason="Image too dark", brightness=bright)
    if bright > 230:
        return QualityReport(ok=False, reason="Image overexposed", brightness=bright)

    return QualityReport(ok=True, blur_score=b_score, brightness=bright)


def bgr_from_upload_bytes(data: bytes) -> np.ndarray:
    """Decode raw uploaded bytes into an OpenCV BGR image."""
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image — file may be corrupt or not an image")
    return image
