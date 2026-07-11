"""
Face detection + encoding + matching, built on face_recognition (dlib).

This is intentionally the *only* module that imports face_recognition.
Everything else in the app talks to this service, not to dlib directly —
so swapping the model later (e.g. to InsightFace) means touching one file.
"""
from dataclasses import dataclass

import face_recognition
import numpy as np

from app.core.config import settings
from app.core.logging import logger


@dataclass
class DetectedFace:
    encoding: np.ndarray                       # 128-d embedding
    box: tuple[int, int, int, int]              # (top, right, bottom, left)


@dataclass
class MatchResult:
    matched_index: int | None   # index into the candidate list, or None
    distance: float
    confidence: float           # 1 - distance, clamped to [0,1]


def detect_faces(image_bgr: np.ndarray, upsample: int = 1) -> list[DetectedFace]:
    """
    Detect all faces in a frame and return their embeddings + bounding boxes.
    `upsample` > 1 helps find small/far-away faces at the cost of speed —
    useful for group/entrance-camera shots, unnecessary for a single selfie.
    """
    # face_recognition expects RGB, OpenCV gives BGR.
    rgb = image_bgr[:, :, ::-1]

    boxes = face_recognition.face_locations(
        rgb, number_of_times_to_upsample=upsample, model="hog"
    )
    if not boxes:
        return []

    encodings = face_recognition.face_encodings(rgb, known_face_locations=boxes)
    return [DetectedFace(encoding=enc, box=box) for enc, box in zip(encodings, boxes)]


def best_match(
    query_encoding: np.ndarray, candidate_encodings: list[np.ndarray]
) -> MatchResult:
    """
    Compare one query embedding against a list of known embeddings
    (typically all encodings belonging to one employee, or the whole
    known-face gallery) and return the closest match.
    """
    if not candidate_encodings:
        return MatchResult(matched_index=None, distance=1.0, confidence=0.0)

    distances = face_recognition.face_distance(candidate_encodings, query_encoding)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])
    confidence = max(0.0, 1.0 - best_distance)

    if best_distance <= settings.FACE_MATCH_THRESHOLD:
        return MatchResult(matched_index=best_idx, distance=best_distance, confidence=confidence)
    return MatchResult(matched_index=None, distance=best_distance, confidence=confidence)


def is_duplicate_face(
    new_encoding: np.ndarray, existing_encodings: list[np.ndarray], strict_threshold: float = 0.35
) -> bool:
    """
    Used during registration to reject near-identical repeat photos, and
    (against the whole-gallery encodings) to stop the same face being
    registered twice under two different employee codes.
    """
    if not existing_encodings:
        return False
    distances = face_recognition.face_distance(existing_encodings, new_encoding)
    return bool(np.min(distances) <= strict_threshold)


def encoding_to_bytes(encoding: np.ndarray) -> bytes:
    return encoding.astype(np.float64).tobytes()


def bytes_to_encoding(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float64)
