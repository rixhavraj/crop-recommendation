from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import chat, recommend, weather, regional
from dotenv import load_dotenv

load_dotenv()


def _parse_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    origins = [origin.strip() for origin in raw_value.split(",")]
    return [origin for origin in origins if origin]

app = FastAPI(
    title="AgriSense API",
    description="India-wide AI crop recommendation and farmer assistant API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(os.getenv("ALLOWED_ORIGINS")),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(recommend.router,
                   prefix="/api",
                   tags=["recommendations"])
app.include_router(weather.router,
                   prefix="/api",
                   tags=["weather"])
app.include_router(regional.router,
                   prefix="/api",
                   tags=["regional"])
app.include_router(chat.router,
                   prefix="/api",
                   tags=["chat"])


@app.get("/")
def root():
    return {"status": "AgriSense API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
