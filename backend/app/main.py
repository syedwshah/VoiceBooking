from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import booking, calls, events, metadata, realtime
from app.utils.config import get_settings

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(title="VoiceBooking API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin)],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(metadata.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(booking.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(realtime.router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
