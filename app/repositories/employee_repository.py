"""
Repository pattern: all direct DB queries for Employee/FaceEncoding live
here. Services call this layer instead of touching the ORM session
directly, which keeps business logic (face_service, attendance_service)
independent of how data happens to be persisted.
"""
import numpy as np
from sqlalchemy.orm import Session

from app.models.employee import Employee, FaceEncoding
from app.services.face_service import bytes_to_encoding, encoding_to_bytes


class EmployeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Employee:
        employee = Employee(**kwargs)
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get(self, employee_id: str) -> Employee | None:
        return self.db.query(Employee).filter(Employee.id == employee_id).first()

    def get_by_code(self, employee_code: str) -> Employee | None:
        return self.db.query(Employee).filter(Employee.employee_code == employee_code).first()

    def list_active(self) -> list[Employee]:
        return self.db.query(Employee).filter(Employee.is_active == True).all()  # noqa: E712

    def add_encoding(
        self, employee_id: str, vector: np.ndarray, source_image_path: str, quality_score: float
    ) -> FaceEncoding:
        row = FaceEncoding(
            employee_id=employee_id,
            vector=encoding_to_bytes(vector),
            source_image_path=source_image_path,
            quality_score=quality_score,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_all_encodings(self) -> list[tuple[FaceEncoding, np.ndarray]]:
        """Returns every stored encoding across all employees, decoded to numpy."""
        rows = self.db.query(FaceEncoding).all()
        return [(row, bytes_to_encoding(row.vector)) for row in rows]

    def get_encodings_for_employee(self, employee_id: str) -> list[np.ndarray]:
        rows = (
            self.db.query(FaceEncoding).filter(FaceEncoding.employee_id == employee_id).all()
        )
        return [bytes_to_encoding(r.vector) for r in rows]
