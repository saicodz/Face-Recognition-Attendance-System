"""
Core runtime endpoint: upload a camera frame, get back who's in it, and
(for anyone confidently recognized) automatically log their attendance.

This is deliberately a single synchronous endpoint rather than a
WebSocket stream — simpler to reason about and test. A live-camera
frontend can just call this every N seconds per frame; a WebSocket
wrapper can be layered on top later without changing this logic.
"""
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.database import get_db
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.attendance import RecognitionMatch, RecognitionResponse
from app.services import face_service
from app.services.attendance_service import mark_attendance
from app.utils.image_utils import bgr_from_upload_bytes

router = APIRouter(prefix="/recognition", tags=["Recognition"])


@router.post("/identify", response_model=RecognitionResponse)
async def identify_and_mark_attendance(
    file: UploadFile = File(...),
    mark: bool = True,
    db: Session = Depends(get_db),
):
    data = await file.read()
    image = bgr_from_upload_bytes(data)

    faces = face_service.detect_faces(image, upsample=1)
    if not faces:
        return RecognitionResponse(faces_detected=0, matches=[], attendance_marked=[])

    emp_repo = EmployeeRepository(db)
    att_repo = AttendanceRepository(db)

    # Build the gallery once per request: (employee_id, employee_code,
    # full_name, encoding) for every stored face across all employees.
    gallery = []
    for enc_row, vector in emp_repo.get_all_encodings():
        gallery.append((enc_row.employee_id, vector))

    matches: list[RecognitionMatch] = []
    marked: list[str] = []

    for face in faces:
        candidate_vectors = [v for _, v in gallery]
        result = face_service.best_match(face.encoding, candidate_vectors)

        if result.matched_index is not None:
            employee_id = gallery[result.matched_index][0]
            employee = emp_repo.get(employee_id)

            matches.append(
                RecognitionMatch(
                    employee_id=employee.id,
                    employee_code=employee.employee_code,
                    full_name=employee.full_name,
                    confidence=round(result.confidence, 4),
                    distance=round(result.distance, 4),
                    is_known=True,
                    face_box=list(face.box),
                )
            )

            if mark:
                snapshot_path = None
                if settings.ATTENDANCE_SNAPSHOTS_DIR.exists():
                    snapshot_path = str(
                        settings.ATTENDANCE_SNAPSHOTS_DIR / f"{uuid.uuid4().hex}.jpg"
                    )
                    import cv2  # local import: only needed on the marking path
                    cv2.imwrite(snapshot_path, image)

                mark_attendance(
                    att_repo,
                    employee_id=employee.id,
                    confidence=result.confidence,
                    snapshot_path=snapshot_path,
                )
                marked.append(employee.employee_code)
        else:
            logger.info(f"Unknown face detected (best distance={result.distance:.3f})")
            matches.append(
                RecognitionMatch(
                    employee_id=None,
                    employee_code=None,
                    full_name=None,
                    confidence=round(result.confidence, 4),
                    distance=round(result.distance, 4),
                    is_known=False,
                    face_box=list(face.box),
                )
            )

    return RecognitionResponse(
        faces_detected=len(faces), matches=matches, attendance_marked=marked
    )
