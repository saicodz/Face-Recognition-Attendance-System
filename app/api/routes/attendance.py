from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.attendance import AttendanceOut

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/today", response_model=list[AttendanceOut])
def today_attendance(db: Session = Depends(get_db)):
    repo = AttendanceRepository(db)
    return repo.list_for_date(date.today())


@router.get("/by-date", response_model=list[AttendanceOut])
def attendance_by_date(day: date = Query(...), db: Session = Depends(get_db)):
    repo = AttendanceRepository(db)
    return repo.list_for_date(day)


@router.get("/employee/{employee_id}", response_model=list[AttendanceOut])
def employee_history(employee_id: str, db: Session = Depends(get_db)):
    emp_repo = EmployeeRepository(db)
    if not emp_repo.get(employee_id):
        raise HTTPException(404, "Employee not found")
    repo = AttendanceRepository(db)
    return repo.list_for_employee(employee_id)
