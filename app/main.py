"""
AL BASSIR Pro — FastAPI Backend
Gateway To Excellence
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv
import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("albassir_api")

from app.routes import (
    auth, formations, categories, sessions,
    inscriptions, students, attendance,
    elearning, quiz, exams, progress, paiements
)
from app.database.connection import init_db
from app.core.limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events"""
    logger.info("Application starting...")
    await init_db()
    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title="AL BASSIR Pro API",
    description="Plateforme E-Learning & Gestion de Formation",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan,
)

# Global exception handler to avoid stack traces in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur serveur globale: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne du serveur s'est produite. Veuillez réessayer plus tard."},
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ─── SÉCURITÉ EN-TÊTES & HOSTS ──────────────────────────────
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "*").split(",")
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ─── CORS ────────────────────────────────────────────────────
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://frontend-school-alpha.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# ─── ROUTES ──────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/auth",        tags=["Auth"])
app.include_router(formations.router,  prefix="/formations",  tags=["Formations"])
app.include_router(categories.router,  prefix="/categories",  tags=["Catégories"])
app.include_router(sessions.router,    prefix="/sessions",    tags=["Sessions"])
app.include_router(inscriptions.router,prefix="/inscriptions",tags=["Inscriptions"])
app.include_router(students.router,    prefix="/students",    tags=["Étudiants"])
app.include_router(attendance.router,  prefix="/attendance",  tags=["Présence"])
app.include_router(elearning.router,   prefix="/elearning",   tags=["E-Learning"])
app.include_router(quiz.router,        prefix="/quiz",        tags=["Quiz"])
app.include_router(exams.router,       prefix="/exams",       tags=["Examens"])
app.include_router(progress.router,    prefix="/progress",    tags=["Progression"])
app.include_router(paiements.router,   prefix="/paiements",   tags=["Paiements"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "app": "AL BASSIR Pro API",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
