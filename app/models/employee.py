"""
Employee + FaceEncoding tables.

Design note: each registered photo produces its own 128-d encoding row
(one-to-many) rather than averaging encodings into a single vector.
Matching against several encodings per person and keeping the best score
is more robust to lighting/angle variation than a single blended vector.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, LargeBinary, Boolean, Float
from sqlalchemy.orm import relationship

from app.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True, default=_uuid)
    employee_code = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    encodings = relationship(
        "FaceEncoding", back_populates="employee", cascade="all, delete-orphan"
    )
    attendance_records = relationship(
        "AttendanceRecord", back_populates="employee", cascade="all, delete-orphan"
    )


class FaceEncoding(Base):
    """
    One row per registered face image. `vector` is a 128-float
    face_recognition/dlib embedding, stored as raw bytes (numpy .tobytes())
    for compactness; reconstructed with np.frombuffer on read.
    """
    __tablename__ = "face_encodings"

    id = Column(String, primary_key=True, default=_uuid)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    vector = Column(LargeBinary, nullable=False)
    source_image_path = Column(String, nullable=False)
    quality_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="encodings")
