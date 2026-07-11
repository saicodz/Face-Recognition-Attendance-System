"""
Employee CRUD + face registration.

Registration flow (POST /employees/{id}/register-face):
  1. Employee must already exist (create via POST /employees first).
  2. Client uploads 3-10 images (different angles/lighting recommended).
  3. Each image is quality-checked (blur, exposure, face size) and
     duplicate-checked against the employee's existing encodings.
  4. Accepted images are saved to disk and their embeddings stored in DB.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.database import get_db
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeOut, RegistrationResult
from app.services import face_service
from app.utils.image_utils import assess_quality, bgr_from_upload_bytes

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    repo = EmployeeRepository(db)
    if repo.get_by_code(payload.employee_code):
        raise HTTPException(409, f"Employee code '{payload.employee_code}' already exists")

    employee = repo.create(**payload.model_dump())
    return EmployeeOut(**employee.__dict__, registered_faces=0)


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    repo = EmployeeRepository(db)
    out = []
    for e in repo.list_active():
        out.append(EmployeeOut(**e.__dict__, registered_faces=len(e.encodings)))
    return out


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    repo = EmployeeRepository(db)
    employee = repo.get(employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    return EmployeeOut(**employee.__dict__, registered_faces=len(employee.encodings))


@router.post("/{employee_id}/register-face", response_model=RegistrationResult)
async def register_face(
    employee_id: str,
    files: list[UploadFile] = File(..., description="3-10 face images"),
    db: Session = Depends(get_db),
):
    repo = EmployeeRepository(db)
    employee = repo.get(employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")

    if len(files) < settings.MIN_REGISTRATION_IMAGES:
        raise HTTPException(
            400,
            f"At least {settings.MIN_REGISTRATION_IMAGES} images required "
            f"(got {len(files)}). Vary angle/lighting between shots.",
        )
    if len(files) > settings.MAX_REGISTRATION_IMAGES:
        files = files[: settings.MAX_REGISTRATION_IMAGES]

    # Existing encodings for this employee (for intra-person duplicate check)
    # and across the whole gallery (to stop one face being registered as
    # two different employees).
    own_encodings = repo.get_encodings_for_employee(employee_id)
    gallery_encodings = [enc for _, enc in repo.get_all_encodings()]

    accepted, rejected = 0, []

    for f in files:
        data = await f.read()
        try:
            image = bgr_from_upload_bytes(data)
        except ValueError as e:
            rejected.append(f"{f.filename}: {e}")
            continue

        faces = face_service.detect_faces(image)
        if len(faces) == 0:
            rejected.append(f"{f.filename}: no face detected")
            continue
        if len(faces) > 1:
            rejected.append(f"{f.filename}: multiple faces detected, expected one")
            continue

        face = faces[0]
        quality = assess_quality(image, face.box)
        if not quality.ok:
            rejected.append(f"{f.filename}: {quality.reason}")
            continue

        if face_service.is_duplicate_face(face.encoding, own_encodings):
            rejected.append(f"{f.filename}: near-duplicate of an already registered photo")
            continue

        # Cross-employee duplicate check (excluding this employee's own encodings,
        # already covered above).
        other_gallery = [
            enc for enc in gallery_encodings if not any((enc == o).all() for o in own_encodings)
        ]
        if face_service.is_duplicate_face(face.encoding, other_gallery, strict_threshold=0.35):
            rejected.append(f"{f.filename}: face appears to match a different employee already")
            continue

        # Persist image to disk
        ext = Path(f.filename or "upload.jpg").suffix or ".jpg"
        save_path = settings.EMPLOYEE_IMAGES_DIR / f"{employee_id}_{uuid.uuid4().hex}{ext}"
        save_path.write_bytes(data)

        repo.add_encoding(
            employee_id=employee_id,
            vector=face.encoding,
            source_image_path=str(save_path),
            quality_score=quality.blur_score,
        )
        own_encodings.append(face.encoding)
        accepted += 1

    logger.info(f"Registration for {employee_id}: accepted={accepted} rejected={len(rejected)}")

    if accepted == 0:
        return RegistrationResult(
            employee_id=employee_id,
            accepted_images=0,
            rejected_images=rejected,
            message="No images were accepted. See rejection reasons for each file.",
        )

    return RegistrationResult(
        employee_id=employee_id,
        accepted_images=accepted,
        rejected_images=rejected,
        message=f"{accepted} image(s) registered successfully.",
    )
