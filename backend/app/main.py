from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    for d in [settings.upload_dir, settings.parsed_dir, settings.results_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Start background cleanup scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from .utils.cleanup import cleanup_expired_sessions

    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_sessions, "interval", minutes=30)
    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from .api.upload import router as upload_router
from .api.datasets import router as datasets_router
from .api.models import router as models_router
from .api.visualization import router as viz_router
from .api.ws import router as ws_router

app.include_router(upload_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(viz_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}


# Serve frontend static files in production (Docker)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not found"}
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
