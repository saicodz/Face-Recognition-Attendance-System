# AI Attendance System — Backend Core

A working FastAPI backend for face-recognition attendance, built on
`face_recognition` (dlib), with clean architecture (routes → services →
repositories → models) so it's easy to extend or swap pieces out later.

## What's actually here

This is the **AI + backend core** only — registration, recognition, and
attendance logic, running on SQLite. It is not the full enterprise spec
(Firebase, React dashboard, notifications, etc.) — see *Roadmap* below for
why, and what's genuinely worth building next.

### Verified working (tests included, all pass in this sandbox)
- Image quality checks: blur detection (Laplacian variance), exposure
  checks, minimum face size — `tests/test_core_logic.py`
- Attendance state machine: first sighting = check-in, later sightings
  update check-out + recompute working hours, late-arrival detection
  against a grace period — `tests/test_attendance_and_db.py`
- Employee/encoding repository + SQLite persistence, full round trip
- Face-matching threshold math (the actual distance/confidence logic used
  by `face_service.best_match`) — `tests/test_matching_math.py` equivalent
  logic, verified with synthetic embeddings

### Not run in this sandbox
`dlib` compiles from C++ source and takes 10–15 minutes on a normal
machine; this sandbox kills background builds between tool calls, so I
could not compile it here. This is expected, not a bug — it's why the
Dockerfile below uses a dedicated build stage. On your machine or in
Docker it installs normally via `pip install -r requirements.txt`.

## Project structure

```
backend/
  app/
    main.py                  # FastAPI app, router registration, startup
    core/
      config.py              # all tunables (thresholds, paths, secrets)
      logging.py             # loguru setup
    models/                  # SQLAlchemy ORM (Employee, FaceEncoding, AttendanceRecord)
    schemas/                 # Pydantic request/response models
    repositories/            # DB access layer (repository pattern)
    services/
      face_service.py        # ONLY file that imports face_recognition/dlib
      attendance_service.py  # check-in/out, late detection, working hours
    utils/
      image_utils.py         # blur/brightness/face-size quality checks
    api/routes/
      employees.py           # create employee, register face images
      recognition.py         # identify faces in a frame, auto-mark attendance
      attendance.py          # query attendance records
  tests/                      # runnable tests, no external services needed
  requirements.txt
  Dockerfile                  # multi-stage build (compiles dlib once, cached)
  docker-compose.yml
```

## Why this design

- **`face_service.py` is the only file that touches dlib.** Swapping to
  InsightFace/ArcFace later (as the original spec suggested) means
  rewriting one file, not the whole app.
- **One row per registered photo, not one averaged vector per employee.**
  Matching against several real encodings and keeping the best score
  handles lighting/angle variation far better than blending vectors.
- **Quality gate before storage.** Blurry, too-small, over/under-exposed,
  or duplicate photos are rejected *before* they become a permanent
  embedding — a bad photo baked into the gallery quietly hurts accuracy
  forever.
- **Attendance is idempotent per (employee, day).** The recognition
  endpoint can be called on every camera frame without creating duplicate
  records — first sighting = check-in, every later sighting refreshes
  check-out and recalculates working hours.

## Running it

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt  # dlib compile: ~10-15 min, be patient
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for interactive Swagger UI.

Or with Docker (recommended — build stage handles the dlib compile once,
and the layer is cached on rebuilds):

```bash
docker compose up --build
```

## Running the tests

```bash
python3 tests/test_core_logic.py          # image quality checks
python3 tests/test_attendance_and_db.py   # attendance state machine + DB
```

## API walkthrough

1. **Create an employee**
   `POST /api/v1/employees` — `{employee_code, full_name, department, ...}`

2. **Register their face** (3–10 photos, different angles/lighting)
   `POST /api/v1/employees/{id}/register-face` — multipart file upload.
   Each photo is quality-checked and duplicate-checked independently;
   the response tells you exactly which were accepted/rejected and why.

3. **Identify + mark attendance from a camera frame**
   `POST /api/v1/recognition/identify` — upload one frame. Every
   confidently-matched face automatically gets attendance logged
   (check-in on first sighting of the day, check-out updated on every
   later one). Unrecognized faces come back as `is_known: false` instead
   of silently failing — that's your hook for an "unknown face" alert.

4. **Query attendance**
   `GET /api/v1/attendance/today`, `/by-date?day=...`,
   `/employee/{id}`

## Configuration

Everything tunable lives in `app/core/config.py` — match threshold,
blur/brightness thresholds, office start time, late-grace-period,
min/max registration images. Override any of it with environment
variables in production instead of editing the file.

## Honest roadmap (what the original spec asked for vs. what's next)

The full spec (Firebase, Next.js dashboard, WebSocket live feed,
liveness/anti-spoofing, DeepSORT tracking, multi-channel notifications,
payroll export, etc.) is a multi-month team project, not something to
fake into existence in one pass. Sensible next slices, roughly in order
of value for an internship portfolio:

1. **JWT auth + role-based access** on top of these routes (admin vs
   viewer) — this is the highest-value next step and fits in cleanly.
2. **A minimal React/Next.js dashboard** hitting these exact endpoints
   (list employees, upload registration photos, live attendance table).
3. **Liveness/anti-spoofing** (e.g. blink detection via MediaPipe) before
   trusting a recognition for attendance — matters a lot for a real
   deployment, currently this system trusts any photo of a registered
   face.
4. **Firebase/Postgres swap** — the repository pattern here means this is
   a repositories-layer change, not a rewrite.
5. **WebSocket streaming** for live camera feeds instead of frame-by-frame
   polling.

I'd rather hand you four things that actually run than fifteen that don't.
