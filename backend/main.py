from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import chat, recommend, weather, regional
from dotenv import load_dotenv

# â”€â”€ Environment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
load_dotenv()

ENV = os.getenv("ENVIRONMENT", "development")          # development | production
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# â”€â”€ Logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agrisense")


# â”€â”€ CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _parse_origins(raw_value: str | None) -> list[str]:
    """Parse comma-separated ALLOWED_ORIGINS env var.
    In production this MUST be set to the Vercel domain(s).
    """
    if not raw_value:
        if ENV == "production":
            logger.warning("ALLOWED_ORIGINS not set in production â€” defaulting to deny-all")
            return []
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ]

    origins = [o.strip() for o in raw_value.split(",") if o.strip()]
    logger.info("CORS origins: %s", origins)
    return origins


# â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = FastAPI(
    title="AgriSense API",
    description="India-wide AI crop recommendation and farmer assistant API",
    version="2.0.0",
    docs_url="/docs" if ENV != "production" else None,       # hide docs in prod
    redoc_url="/redoc" if ENV != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(os.getenv("ALLOWED_ORIGINS")),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)


# â”€â”€ Request logging middleware â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response

@app.on_event("startup")
def warm_up_runtime():
    """Preload heavy ML modules so first recommendation request is faster."""
    try:
        import ml.predict  # noqa: F401
        logger.info("ML prediction module preloaded")
    except Exception as exc:
        logger.warning("ML preload skipped: %s", exc)

# â”€â”€ Global exception handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# â”€â”€ Routers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.include_router(recommend.router, prefix="/api", tags=["recommendations"])
app.include_router(weather.router,   prefix="/api", tags=["weather"])
app.include_router(regional.router,  prefix="/api", tags=["regional"])
app.include_router(chat.router,      prefix="/api", tags=["chat"])


# â”€â”€ Health & Root â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MODELS_DIR = Path(__file__).resolve().parent / "models"


@app.get("/api")
def root():
    return {"status": "AgriSense API is running", "version": "2.0.0"}


@app.get("/api/health")
def health():
    """Deep health check â€” validates model files, data files, and memory."""
    checks = {}

    # Model file
    model_path = MODELS_DIR / "crop_model.pkl"
    checks["model_loaded"] = model_path.exists()

    # Encoder file
    encoder_path = MODELS_DIR / "encoders.pkl"
    checks["encoders_loaded"] = encoder_path.exists()

    # Data directory
    data_dir = Path(__file__).resolve().parent / "data"
    checks["crop_db"] = (data_dir / "crop_db.json").exists()
    checks["locations"] = (data_dir / "india_locations.json").exists()

    all_ok = all(checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "environment": ENV,
        "checks": checks,
    }

