import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import models  # noqa: F401  (registers tables)
from .db import Base, engine
from .latency import SimulatedLatencyMiddleware
from .routers import bookings, rooms, users

SIMULATED_LATENCY_MS = int(os.getenv("SIMULATED_LATENCY_MS", "0"))
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="RoomBook", lifespan=lifespan)
app.add_middleware(SimulatedLatencyMiddleware, max_ms=SIMULATED_LATENCY_MS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(users.router)
app.include_router(bookings.router)


@app.get("/health")
def health():
    """Readiness check: report healthy only when the database responds."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}


@app.get("/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
def readiness():
    return health()
