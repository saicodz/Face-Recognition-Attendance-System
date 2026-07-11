"""
Application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs for interactive Swagger UI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.models.database import init_db
from app.api.routes import employees, recognition, attendance

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered face recognition attendance system — core engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to real frontend origin(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employees.router, prefix=settings.API_V1_PREFIX)
app.include_router(recognition.router, prefix=settings.API_V1_PREFIX)
app.include_router(attendance.router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info(f"{settings.APP_NAME} started (env={settings.ENV})")


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
