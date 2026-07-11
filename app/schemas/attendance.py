from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RecognitionMatch(BaseModel):
    employee_id: Optional[str]
    employee_code: Optional[str]
    full_name: Optional[str]
    confidence: float           # 0..1, higher = more confident
    distance: float             # raw face distance, lower = closer match
    is_known: bool
    face_box: list[int]         # [top, right, bottom, left] in the frame


class RecognitionResponse(BaseModel):
    faces_detected: int
    matches: list[RecognitionMatch]
    attendance_marked: list[str]   # employee_codes for which attendance was logged


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    status: str
    working_hours: float
    confidence_score: Optional[float]
