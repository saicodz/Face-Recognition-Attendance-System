"""
Central application configuration.

All tunable parameters (thresholds, paths, secrets) live here so the rest
of the codebase never hardcodes magic numbers. Values can be overridden
via environment variables (see pydantic-settings docs) which is what you
want in Docker / production deployments.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "AI Attendance System"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- Storage ---
    STORAGE_DIR: Path = BASE_DIR / "storage"
    EMPLOYEE_IMAGES_DIR: Path = STORAGE_DIR / "employee_images"
    ATTENDANCE_SNAPSHOTS_DIR: Path = STORAGE_DIR / "attendance_snapshots"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'storage' / 'attendance.db'}"

    # --- Face recognition tuning ---
    # Lower = stricter match. 0.6 is the face_recognition library default;
    # 0.5 trades a few more false-rejects for far fewer false-accepts,
    # which is the right trade for an attendance system.
    FACE_MATCH_THRESHOLD: float = 0.50

    # Minimum images required to register an employee reliably across
    # lighting/angle variation.
    MIN_REGISTRATION_IMAGES: int = 3
    MAX_REGISTRATION_IMAGES: int = 10

    # Laplacian-variance blur threshold. Frames scoring below this are
    # rejected as too blurry to produce a trustworthy embedding.
    BLUR_THRESHOLD: float = 80.0

    # Minimum face bounding box size (pixels) relative to a 720p-ish frame,
    # to reject faces that are too small/far away to encode reliably.
    MIN_FACE_SIZE_PX: int = 60

    # --- Attendance policy ---
    OFFICE_START_TIME: str = "09:30"  # HH:MM, 24h
    LATE_GRACE_MINUTES: int = 15
    STANDARD_WORK_HOURS: float = 8.0

    # --- Security ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure storage directories exist at import time.
settings.EMPLOYEE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
settings.ATTENDANCE_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
