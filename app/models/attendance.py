import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import relationship

from app.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AttendanceRecord(Base):
    """
    One row per employee per day. check_in is set on the first recognized
    entry of the day; check_out is updated on every subsequent recognition
    (so the last sighting of the day becomes the exit time), matching how
    a real camera-based system behaves.
    """
    __tablename__ = "attendance_records"

    id = Column(String, primary_key=True, default=_uuid)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)

    status = Column(String, default="present")  # present | late | absent
    working_hours = Column(Float, default=0.0)
    confidence_score = Column(Float, nullable=True)
    snapshot_path = Column(String, nullable=True)

    employee = relationship("Employee", back_populates="attendance_records")
