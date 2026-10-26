import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes.plan import router as plan_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("celebration-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup and once on shutdown."""
    if not settings.GEMINI_API_KEY:
        logger.warning(
            "GEMINI_API_KEY is not set. /generate-plan will return fallback plans."
        )
    else:
        logger.info(f"GEMINI_API_KEY loaded. Model: {settings.GEMINI_MODEL}")
        logger.info(f"Fallback models: {settings.GEMINI_FALLBACK_MODELS}")
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting up.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "GenAI-powered backend that turns event inputs into structured "
        "budgets, timelines, vendor checklists, and personalized ideas."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS: allow everything for the hackathon ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Fallback-Used"],  # lets browsers read our debug header
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(plan_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all so the frontend always receives structured JSON."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error. Please try again.",
            "path": str(request.url.path),
        },
    )


@app.get("/", tags=["meta"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "generate_plan": "/api/v1/generate-plan",
    }


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "model": settings.GEMINI_MODEL,
        "force_fallback": getattr(settings, "FORCE_FALLBACK", False),
    }