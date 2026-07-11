"""
Database engine + session factory. Swappable: change DATABASE_URL in
config.py to point at Postgres/MySQL instead of SQLite without touching
any other file, since everything else talks to the ORM, not the driver.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and guarantees it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once on app startup."""
    from app.models import employee, attendance  # noqa: F401 (register models)
    Base.metadata.create_all(bind=engine)
