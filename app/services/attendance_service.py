"""
Attendance business rules: first sighting of the day = check-in, every
later sighting updates check-out + recalculates working hours, and the
first sighting is compared against the office start time (+ grace period)
to flag late arrivals.
"""
from datetime import datetime, date, time

from app.core.config import settings
from app.core.logging import logger
from app.repositories.attendance_repository import AttendanceRepository


def _office_start_datetime(day: date) -> datetime:
    hh, mm = map(int, settings.OFFICE_START_TIME.split(":"))
    return datetime.combine(day, time(hour=hh, minute=mm))


def mark_attendance(
    repo: AttendanceRepository,
    employee_id: str,
    confidence: float,
    snapshot_path: str | None,
    when: datetime | None = None,
):
    """
    Idempotent per (employee, day): safe to call on every recognized frame.
    Returns (record, event) where event is "check_in" or "check_out_updated".
    """
    when = when or datetime.utcnow()
    today = when.date()

    existing = repo.get_today_record(employee_id, today)

    if existing is None:
        office_start = _office_start_datetime(today)
        grace_cutoff = office_start.timestamp() + settings.LATE_GRACE_MINUTES * 60
        status = "late" if when.timestamp() > grace_cutoff else "present"

        record = repo.create(
            employee_id=employee_id,
            date=today,
            check_in=when,
            status=status,
            confidence_score=confidence,
            snapshot_path=snapshot_path,
        )
        logger.info(f"Check-in recorded for employee={employee_id} status={status}")
        return record, "check_in"

    record = repo.update_checkout(existing, when, confidence)
    return record, "check_out_updated"
