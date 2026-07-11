import sys
import types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
import os

# --- Stub out face_recognition/dlib for this test run ---
# This test file exercises DB + attendance business logic only, which
# doesn't need real face matching, so we stub the dependency rather than
# requiring a full dlib compile just to run these tests.
stub = types.ModuleType("face_recognition")
stub.face_locations = lambda *a, **k: []
stub.face_encodings = lambda *a, **k: []
stub.face_distance = lambda known, query: []
sys.modules["face_recognition"] = stub

# Use a throwaway sqlite file for this test run
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/test_attendance.db")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base
from app.models.employee import Employee, FaceEncoding  # noqa
from app.models.attendance import AttendanceRecord  # noqa
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.services.attendance_service import mark_attendance

engine = create_engine("sqlite:////tmp/test_attendance.db", connect_args={"check_same_thread": False})
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

emp_repo = EmployeeRepository(db)
att_repo = AttendanceRepository(db)

# 1. Create employee
emp = emp_repo.create(employee_code="EMP001", full_name="Asha Rao", department="Engineering")
assert emp.id is not None
print(f"PASS employee created: {emp.employee_code}")

# 2. Duplicate employee_code should be catchable by caller (repo itself doesn't enforce -> route does)
found = emp_repo.get_by_code("EMP001")
assert found.id == emp.id
print("PASS lookup by employee_code works")

# 3. First check-in before grace cutoff -> status "present"
on_time = datetime.combine(datetime.today().date(), datetime.min.time().replace(hour=9, minute=20))
record, event = mark_attendance(att_repo, emp.id, confidence=0.9, snapshot_path=None, when=on_time)
assert event == "check_in"
assert record.status == "present", record.status
print(f"PASS on-time check-in -> status={record.status}")

# 4. Second sighting same day updates check_out + working_hours, doesn't duplicate row
later = on_time.replace(hour=17, minute=20)
record2, event2 = mark_attendance(att_repo, emp.id, confidence=0.95, snapshot_path=None, when=later)
assert event2 == "check_out_updated"
assert record2.id == record.id, "should update same day's record, not create a new one"
assert abs(record2.working_hours - 8.0) < 0.01, record2.working_hours
print(f"PASS check-out updates same record, working_hours={record2.working_hours}")

# 5. New employee arriving late (past 09:30 + 15 min grace) -> status "late"
emp2 = emp_repo.create(employee_code="EMP002", full_name="Vikram Shah")
late_time = datetime.combine(datetime.today().date(), datetime.min.time().replace(hour=10, minute=0))
record3, _ = mark_attendance(att_repo, emp2.id, confidence=0.8, snapshot_path=None, when=late_time)
assert record3.status == "late", record3.status
print(f"PASS late arrival correctly flagged -> status={record3.status}")

# 6. list_for_date returns both employees' records
todays = att_repo.list_for_date(on_time.date())
assert len(todays) == 2
print("PASS list_for_date returns all records for the day")

db.close()
os.remove("/tmp/test_attendance.db")
print("\nALL ATTENDANCE + DB TESTS PASSED")
