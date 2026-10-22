import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.migrations import apply_migrations

# Create tables if not existing
Base.metadata.create_all(bind=engine)
# Safely apply any missing column migrations to existing SQLite databases
apply_migrations(engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API for AI-powered Job Search and Auto-Apply Platform (Module 1)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
cors_origins = list(settings.CORS_ORIGINS)
render_external_url = os.getenv("RENDER_EXTERNAL_URL")
if render_external_url and render_external_url not in cors_origins:
    cors_origins.append(render_external_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


def resolve_frontend_dist() -> Optional[str]:
    """Resolves the absolute path to the compiled New Frontend/dist directory."""
    # 1. Environment variable override
    env_dir = os.getenv("FRONTEND_DIST_DIR")
    if env_dir and os.path.isdir(env_dir):
        return os.path.abspath(env_dir)

    # 2. Relative to backend/app/main.py (2 levels up to repo root, then New Frontend/dist)
    app_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(app_dir)
    repo_root = os.path.dirname(backend_dir)
    candidate = os.path.join(repo_root, "New Frontend", "dist")
    if os.path.isdir(candidate):
        return os.path.abspath(candidate)

    # 3. Relative to current working directory
    cwd_candidate = os.path.join(os.getcwd(), "New Frontend", "dist")
    if os.path.isdir(cwd_candidate):
        return os.path.abspath(cwd_candidate)

    # 4. If cwd is New Frontend/dist directly
    if os.path.isfile(os.path.join(os.getcwd(), "index.html")) and os.path.isdir(os.path.join(os.getcwd(), "assets")):
        return os.path.abspath(os.getcwd())

    return None


frontend_dist = resolve_frontend_dist()

if frontend_dist and os.path.isfile(os.path.join(frontend_dist, "index.html")):
    # Mount Vite static assets directory (/assets)
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        """Serves the React frontend index.html on root access."""
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": "1.0.0",
            "docs": "/docs"
        }

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_or_static(full_path: str):
        """
        Serves exact static files if present in dist/, otherwise falls back to index.html
        for client-side React SPA routing. Strictly excludes API routes, documentation,
        and system health endpoints from SPA fallback.
        """
        api_prefix = settings.API_V1_STR.lstrip("/")
        # Protect API routes and documentation endpoints from HTML fallback
        if (
            full_path.startswith("api/")
            or full_path == "api"
            or full_path.startswith(f"{api_prefix}/")
            or full_path == api_prefix
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        if full_path in ("docs", "redoc", "openapi.json", "health"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Serve static file if an exact match exists in dist/ (e.g., favicon.ico, manifest.json)
        candidate_file = os.path.join(frontend_dist, full_path)
        if os.path.isfile(candidate_file):
            return FileResponse(candidate_file)

        # Serve React SPA index.html for client-side navigation
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)

        raise HTTPException(status_code=404, detail="Not Found")
else:
    @app.get("/", tags=["Health"])
    def root():
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": "1.0.0",
            "docs": "/docs"
        }
