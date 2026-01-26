"""
Harry Bot Dashboard - FastAPI Application
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routes import router
from .auth import auth_router

logger = logging.getLogger('Dashboard')

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    logger.info("🚀 Harry Dashboard starting up...")
    yield
    logger.info("👋 Harry Dashboard shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    app = FastAPI(
        title="Harry Bot Dashboard",
        description="Manage Harry bot settings for your Discord servers",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware - restrict to specific origins in production
    allowed_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # ["https://yourdomain.com"] in production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Session middleware for OAuth
    secret_key = os.getenv('DASHBOARD_SECRET_KEY', os.urandom(32).hex())
    app.add_middleware(SessionMiddleware, secret_key=secret_key)

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(router, tags=["dashboard"])

    @app.get("/")
    async def root(request: Request):
        """Redirect to dashboard or login"""
        user = request.session.get("user")
        if user:
            return RedirectResponse(url="/dashboard")
        return RedirectResponse(url="/auth/login")

    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "service": "harry-dashboard"}

    return app


# Create app instance for running directly
app = create_app()
