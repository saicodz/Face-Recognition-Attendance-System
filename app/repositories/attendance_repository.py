from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord


class AttendanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_today_record(self, employee_id: str, day: date) -> AttendanceRecord | None:
        return (
            self.db.query(AttendanceRecord)
            .filter(AttendanceRecord.employee_id == employee_id, AttendanceRecord.date == day)
            .first()
        )

    def create(self, **kwargs) -> AttendanceRecord:
        record = AttendanceRecord(**kwargs)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_checkout(
        self, record: AttendanceRecord, checkout_time: datetime, confidence: float
    ) -> AttendanceRecord:
        record.check_out = checkout_time
        record.confidence_score = max(record.confidence_score or 0, confidence)
        if record.check_in:
            delta = checkout_time - record.check_in
            record.working_hours = round(delta.total_seconds() / 3600, 2)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_for_date(self, day: date) -> list[AttendanceRecord]:
        return self.db.query(AttendanceRecord).filter(AttendanceRecord.date == day).all()

    def list_for_employee(self, employee_id: str, limit: int = 30) -> list[AttendanceRecord]:
        return (
            self.db.query(AttendanceRecord)
            .filter(AttendanceRecord.employee_id == employee_id)
            .order_by(AttendanceRecord.date.desc())
            .limit(limit)
            .all()
        )
