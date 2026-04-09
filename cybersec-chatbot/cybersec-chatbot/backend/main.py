"""
main.py — FastAPI application entry point.

Start with:
  uvicorn backend.main:app --reload --port 8000

Production:
  gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .database import connect_db, close_db
from .routers import chat, analyze
from .utils.logger import get_logger

settings = get_settings()
logger = get_logger("main")
limiter = Limiter(key_func=get_remote_address)


# ── Application lifespan (startup / shutdown) ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CyberGuard API...")
    try:
        await connect_db()
        logger.info("MongoDB connection established.")
    except Exception as exc:
        logger.warning(f"MongoDB unavailable — running without persistence: {exc}")
    yield
    logger.info("Shutting down CyberGuard API...")
    await close_db()


# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(
    title="CyberGuard Chatbot API",
    description=(
        "AI-powered cybersecurity awareness chatbot. "
        "Detects phishing, malware, and social engineering threats."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────
# CORS middleware must be added BEFORE rate limiter to allow OPTIONS preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Global error handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(analyze.router)



# ── Frontend serving ───────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/", tags=["Frontend"])
async def serve_frontend() -> FileResponse:
    """Serve the frontend index.html."""
    return FileResponse(frontend_path / "index.html")


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Simple liveness probe — used by load balancers and Docker health checks."""
    return {"status": "ok", "service": "CyberGuard API", "version": "1.0.0"}
